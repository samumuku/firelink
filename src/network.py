import socket
import threading
import time
import json

# --- CONFIGURATION ---
BROADCAST_IP = "255.255.255.255"
DISCOVERY_PORT = 12345

class PeerDiscovery:
    def __init__(self, username, on_peer_found, on_db_update=None):
        self.username = username
        self.on_peer_found = on_peer_found
        self.on_db_update = on_db_update # Callback for when the Shared DB changes
        self.running = True
        
        # THE SHARED DATABASE (Stores files everyone is sharing)
        # Format: { "filename": { "owner": "Mike", "ip": "25.x.x.x", "size": "2GB" } }
        self.shared_db = {} 

        # Setup Socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.bind(("", DISCOVERY_PORT))

    def start(self):
        threading.Thread(target=self.listen_loop, daemon=True).start()
        threading.Thread(target=self.broadcast_loop, daemon=True).start()

    def share_file_announcement(self, filename, size):
        """Call this when YOU want to share a file with the group"""
        # 1. Update my local list
        file_info = {"owner": self.username, "ip": "MY_IP", "size": size} 
        self.shared_db[filename] = file_info
        
        # 2. Shout it to the network
        msg = {
            "type": "ADD_FILE",
            "user": self.username,
            "data": {"name": filename, "info": file_info}
        }
        self.send_json(msg)

    def send_json(self, data_dict):
        """Helper to send JSON data safely"""
        try:
            msg_str = json.dumps(data_dict)
            self.sock.sendto(msg_str.encode(), (BROADCAST_IP, DISCOVERY_PORT))
        except Exception as e:
            print(f"Send Error: {e}")

    def broadcast_loop(self):
        """The Mouth: Shouts 'I am here' every 3 seconds"""
        while self.running:
            msg = {
                "type": "HELLO",
                "user": self.username
            }
            self.send_json(msg)
            time.sleep(3)

    def listen_loop(self):
        """The Ear: Listens for Friends and Files"""
        while self.running:
            try:
                data, addr = self.sock.recvfrom(4096)
                try:
                    msg = json.loads(data.decode())
                except: continue # Skip junk data

                sender_ip = addr[0]
                sender_name = msg.get("user")
                msg_type = msg.get("type")

                # Don't listen to myself
                if sender_name == self.username:
                    continue

                # 1. If it's a Hello, add them to friends list
                if msg_type == "HELLO":
                    self.on_peer_found(sender_name, sender_ip)

                # 2. If it's a File Announcement, add to database
                elif msg_type == "ADD_FILE":
                    file_data = msg.get("data")
                    fname = file_data["name"]
                    finfo = file_data["info"]
                    
                    # Ensure the IP is the actual sender's IP
                    finfo["ip"] = sender_ip 
                    
                    self.shared_db[fname] = finfo
                    # Trigger the GUI update if it exists
                    if self.on_db_update:
                        self.on_db_update(self.shared_db)

            except Exception as e:
                print(f"Listen Error: {e}")