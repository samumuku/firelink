import socket
import threading
import time
import json

# --- CONFIGURATION ---
DISCOVERY_PORT = 12345

class PeerDiscovery:
    def __init__(self, username, on_peer_found, on_db_update=None):
        self.username = username
        self.on_peer_found = on_peer_found
        self.on_db_update = on_db_update
        self.running = True
        
        self.machine_name = socket.gethostname()
        self.shared_db = {} 

        # Setup Socket
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        # Bind to all interfaces
        self.sock.bind(("", DISCOVERY_PORT))

    def start(self):
        threading.Thread(target=self.listen_loop, daemon=True).start()
        threading.Thread(target=self.broadcast_loop, daemon=True).start()

    def get_broadcast_targets(self):
        """
        Identify all network interfaces and calculate their broadcast addresses.
        This ensures the packet goes into the VPN tunnel, not just the WiFi.
        """
        targets = ["255.255.255.255"] # Always try global default
        try:
            # Get all IP addresses associated with this computer
            hostname = socket.gethostname()
            local_ips = socket.gethostbyname_ex(hostname)[2]
            
            for ip in local_ips:
                # Calculate broadcast based on common VPN patterns
                parts = ip.split('.')
                
                # Hamachi usually uses 25.x.x.x
                if parts[0] == '25':
                    targets.append("25.255.255.255")
                
                # Radmin VPN usually uses 26.x.x.x
                elif parts[0] == '26':
                    targets.append("26.255.255.255")
                
                # ZeroTier usually uses 10.x.x.x (Class A)
                elif parts[0] == '10':
                    targets.append("10.255.255.255")
                    
                # Standard Home Network (192.168.x.x)
                elif parts[0] == '192' and parts[1] == '168':
                    targets.append(f"192.168.{parts[2]}.255")
                    
                # Standard Class B (172.16-31.x.x)
                elif parts[0] == '172':
                    targets.append(f"172.{parts[1]}.255.255")
                    
        except Exception:
            pass
            
        return list(set(targets)) # Remove duplicates

    def share_file_announcement(self, filename, size):
        file_info = {"owner": self.username, "ip": "MY_IP", "size": size} 
        self.shared_db[filename] = file_info
        
        msg = {
            "type": "ADD_FILE",
            "user": self.username,
            "data": {"name": filename, "info": file_info}
        }
        self.send_json(msg)

    def send_json(self, data_dict):
        """Send the message to ALL calculated broadcast targets"""
        try:
            msg_str = json.dumps(data_dict)
            encoded_msg = msg_str.encode()
            
            # The Shotgun Approach: Send to every possible broadcast address
            targets = self.get_broadcast_targets()
            
            for target_ip in targets:
                try:
                    self.sock.sendto(encoded_msg, (target_ip, DISCOVERY_PORT))
                except OSError:
                    # Some interfaces might fail (e.g., if disconnected), just ignore
                    pass
                    
        except Exception as e:
            print(f"Send Error: {e}")

    def broadcast_loop(self):
        while self.running:
            msg = {
                "type": "HELLO",
                "user": self.username,
                "machine": self.machine_name
            }
            self.send_json(msg)
            time.sleep(3)

    def listen_loop(self):
        while self.running:
            try:
                data, addr = self.sock.recvfrom(4096)
                try:
                    msg = json.loads(data.decode())
                except: continue 

                sender_ip = addr[0]
                sender_name = msg.get("user", "Unknown")
                sender_machine = msg.get("machine", "Unknown Machine")
                msg_type = msg.get("type")

                if sender_name == self.username:
                    continue

                if msg_type == "HELLO":
                    # Using display name composition from previous context
                    display_name = f"{sender_name} ({sender_machine})"
                    self.on_peer_found(display_name, sender_ip)

                elif msg_type == "ADD_FILE":
                    file_data = msg.get("data")
                    fname = file_data["name"]
                    finfo = file_data["info"]
                    finfo["ip"] = sender_ip 
                    
                    self.shared_db[fname] = finfo
                    if self.on_db_update:
                        self.on_db_update(self.shared_db)

            except Exception as e:
                print(f"Listen Error: {e}")