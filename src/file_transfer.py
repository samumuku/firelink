import socket
import os
import threading

# --- CONFIGURATION ---
TCP_PORT = 5001
BUFFER_SIZE = 4096
SEPARATOR = "<SEPARATOR>"

class FileTransfer:
    def __init__(self, download_folder="Downloads"):
        self.download_folder = download_folder
        if not os.path.exists(self.download_folder):
            os.makedirs(self.download_folder)

    def start_receiver(self, on_status_update, on_progress_update):
        """Starts listening for incoming files in the background"""
        thread = threading.Thread(target=self._receiver_loop, 
                                  args=(on_status_update, on_progress_update), 
                                  daemon=True)
        thread.start()

    def _receiver_loop(self, on_status_update, on_progress_update):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Allow reusing the port immediately if you restart the app
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            server_socket.bind(("0.0.0.0", TCP_PORT))
        except Exception as e:
            print(f"Receiver Error: {e}")
            return

        server_socket.listen(5)
        print(f"[*] Listening for files on port {TCP_PORT}")

        while True:
            # Accept Connection
            client_socket, address = server_socket.accept()
            print(f"[+] Connection from {address}")
            
            try:
                # Read Metadata (Filename & Size)
                received = client_socket.recv(BUFFER_SIZE).decode()
                filename, filesize = received.split(SEPARATOR)
                filename = os.path.basename(filename) # Remove folder paths for security
                filesize = int(filesize)

                on_status_update(f"Receiving: {filename}")
                
                # Receive File Data
                save_path = os.path.join(self.download_folder, filename)
                progress = 0

                with open(save_path, "wb") as f:
                    while True:
                        bytes_read = client_socket.recv(BUFFER_SIZE)
                        if not bytes_read:
                            break
                        f.write(bytes_read)
                        progress += len(bytes_read)
                        
                        # Update Progress Bar (0.0 to 1.0)
                        if on_progress_update:
                            on_progress_update(progress / filesize)
                            
                        if progress >= filesize:
                            break
                            
                on_status_update(f"Saved: {filename}")
                print(f"[+] File saved to {save_path}")

            except Exception as e:
                print(f"Transfer Error: {e}")
            finally:
                client_socket.close()


    def send_file(self, ip, filepath, on_status_update, on_progress_update):
        """Starts sending a file in a background thread"""
        thread = threading.Thread(target=self._sender_thread, 
                                  args=(ip, filepath, on_status_update, on_progress_update), 
                                  daemon=True)
        thread.start()

    def _sender_thread(self, ip, filepath, on_status_update, on_progress_update):
        try:
            filesize = os.path.getsize(filepath)
            filename = os.path.basename(filepath)
            
            on_status_update(f"Connecting to {ip}...")
            
            # Connect
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((ip, TCP_PORT))
            
            # Send Metadata
            s.send(f"{filename}{SEPARATOR}{filesize}".encode())
            
            # Send File Data
            on_status_update(f"Sending {filename}...")
            sent_bytes = 0
            
            with open(filepath, "rb") as f:
                while True:
                    bytes_read = f.read(BUFFER_SIZE)
                    if not bytes_read:
                        break
                    s.sendall(bytes_read)
                    sent_bytes += len(bytes_read)
                    
                    # Update Progress
                    if on_progress_update:
                        on_progress_update(sent_bytes / filesize)
            
            s.close()
            on_status_update("Transfer Complete!")
            
        except Exception as e:
            on_status_update(f"Error: {str(e)}")
            print(f"Send Error: {e}")