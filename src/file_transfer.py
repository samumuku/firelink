import socket
import os
import threading
import utils

# --- CONFIGURATION ---
TCP_PORT = 5001
BUFFER_SIZE = 4096
SEPARATOR = "<SEPARATOR>"

class FileTransfer:
    def __init__(self, download_folder="Downloads"):
        self.download_folder = download_folder
        if not os.path.exists(self.download_folder):
            os.makedirs(self.download_folder)

    # --- RECEIVER (MODIFIED) ---
    def start_receiver(self, on_status_update, on_progress_update, on_permission_request):
        """
        on_permission_request: callback(filename, sender_ip, filesize, response_event, response_container)
        """
        thread = threading.Thread(target=self._receiver_loop, 
                                  args=(on_status_update, on_progress_update, on_permission_request), 
                                  daemon=True)
        thread.start()

    def _receiver_loop(self, on_status_update, on_progress_update, on_permission_request):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            server_socket.bind(("0.0.0.0", TCP_PORT))
        except Exception as e:
            print(f"Receiver Error: {e}")
            return

        server_socket.listen(5)
        print(f"[*] Listening on {TCP_PORT}")

        while True:
            client_socket, address = server_socket.accept()
            ip = address[0]
            
            # 1. Block Check
            if utils.is_blocked(ip):
                client_socket.close()
                continue
            
            # Handle each transfer in a separate thread so multiple requests don't freeze the listener
            t = threading.Thread(target=self._handle_incoming_client, 
                                 args=(client_socket, ip, on_status_update, on_progress_update, on_permission_request),
                                 daemon=True)
            t.start()

    def _handle_incoming_client(self, client_socket, ip, on_status_update, on_progress_update, on_permission_request):
        try:
            # 2. Read Metadata
            received = client_socket.recv(BUFFER_SIZE).decode()
            if not received: return
            filename, filesize = received.split(SEPARATOR)
            filename = os.path.basename(filename)
            filesize = int(filesize)

            # 3. ASK PERMISSION (Blocking Wait)
            response_event = threading.Event()
            response_container = {"allow": False} # Mutable dict to store result
            
            # Call GUI callback (This should trigger a popup)
            on_permission_request(filename, ip, filesize, response_event, response_container)
            
            # Wait until user clicks a button
            response_event.wait() 

            if not response_container["allow"]:
                # User Declined
                client_socket.send("REJECT".encode())
                on_status_update(f"Declined transfer from {ip}")
                client_socket.close()
                return

            # User Accepted
            client_socket.send("ACK".encode()) # Tell sender to start
            on_status_update(f"Receiving: {filename}")

            # 4. Receive File Data
            save_path = os.path.join(self.download_folder, filename)
            
            # Handle duplicate names
            base, ext = os.path.splitext(save_path)
            counter = 1
            while os.path.exists(save_path):
                save_path = f"{base}_{counter}{ext}"
                counter += 1

            progress = 0
            with open(save_path, "wb") as f:
                while True:
                    bytes_read = client_socket.recv(BUFFER_SIZE)
                    if not bytes_read: break
                    f.write(bytes_read)
                    progress += len(bytes_read)
                    if on_progress_update: on_progress_update(progress / filesize)
                    if progress >= filesize: break
                            
            on_status_update(f"Saved: {os.path.basename(save_path)}")

        except Exception as e:
            print(f"Transfer Error: {e}")
        finally:
            client_socket.close()

    # --- SENDER (MODIFIED) ---
    def send_file(self, ip, filepath, on_status_update, on_progress_update):
        thread = threading.Thread(target=self._sender_thread, 
                                  args=(ip, filepath, on_status_update, on_progress_update), 
                                  daemon=True)
        thread.start()

    def _sender_thread(self, ip, filepath, on_status_update, on_progress_update):
        try:
            filesize = os.path.getsize(filepath)
            filename = os.path.basename(filepath)
            
            on_status_update(f"Requesting to send to {ip}...")
            
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((ip, TCP_PORT))
            
            # 1. Send Metadata
            s.send(f"{filename}{SEPARATOR}{filesize}".encode())
            
            # 2. WAIT for Permission (Handshake)
            on_status_update("Waiting for user to accept...")
            response = s.recv(1024).decode()
            
            if response != "ACK":
                on_status_update("Transfer declined by user.")
                s.close()
                return

            # 3. Send Data
            on_status_update(f"Sending {filename}...")
            sent_bytes = 0
            with open(filepath, "rb") as f:
                while True:
                    bytes_read = f.read(BUFFER_SIZE)
                    if not bytes_read: break
                    s.sendall(bytes_read)
                    sent_bytes += len(bytes_read)
                    if on_progress_update: on_progress_update(sent_bytes / filesize)
            
            s.close()
            on_status_update("Transfer Complete!")
            
        except Exception as e:
            on_status_update(f"Error: {str(e)}")
            print(f"Send Error: {e}")