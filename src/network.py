import socket
import threading
import time
import json
import uuid

# --- CONFIGURATION ---
DISCOVERY_PORT = 12345

class PeerDiscovery:
    def __init__(self, username, on_peer_found, on_db_update=None):
        self.username = username
        self.on_peer_found = on_peer_found
        self.on_db_update = on_db_update
        self.running = True
        self.peer_id = str(uuid.uuid4())
        
        self.machine_name = socket.gethostname()
        self.shared_db = {} 

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.bind(("", DISCOVERY_PORT))

    def start(self):
        threading.Thread(target=self.listen_loop, daemon=True).start()
        # We run BOTH Broadcast (for normal networks) AND Scan (for strict networks)
        threading.Thread(target=self.broadcast_loop, daemon=True).start()
        threading.Thread(target=self.scan_loop, daemon=True).start()

    def get_local_subnets(self):
        """Finds the base IP (e.g., 192.168.1) for all adapters"""
        subnets = []
        try:
            hostname = socket.gethostname()
            local_ips = socket.gethostbyname_ex(hostname)[2]
            for ip in local_ips:
                parts = ip.split('.')
                # Only care about standard IPv4 
                if len(parts) == 4:
                    # Store "192.168.1"
                    base = f"{parts[0]}.{parts[1]}.{parts[2]}"
                    subnets.append(base)
        except: pass
        return subnets

    def send_packet(self, target_ip, data_dict):
        try:
            data_dict["peer_id"] = self.peer_id
            msg = json.dumps(data_dict).encode()
            self.sock.sendto(msg, (target_ip, DISCOVERY_PORT))
        except: pass

    def scan_loop(self):
        """The Brute Force: Sends a packet to .1 through .254 individually"""
        while self.running:
            msg = {
                "type": "HELLO",
                "user": self.username,
                "machine": self.machine_name
            }
            
            subnets = self.get_local_subnets()
            for base_ip in subnets:
                # Loop through 1 to 254 (Standard Home/Hotspot range)
                for i in range(1, 255):
                    target = f"{base_ip}.{i}"
                    self.send_packet(target, msg)
                    # Tiny sleep to prevent crashing the router
                    time.sleep(0.005) 
            
            # Wait 10 seconds before scanning again (so we don't lag the network)
            time.sleep(10)

    def broadcast_loop(self):
        """Standard Broadcast (Kept as backup)"""
        while self.running:
            msg = {
                "type": "HELLO",
                "user": self.username,
                "machine": self.machine_name
            }
            # Try global broadcast
            self.send_packet("255.255.255.255", msg)
            time.sleep(3)

    def listen_loop(self):
        while self.running:
            try:
                data, addr = self.sock.recvfrom(4096)
                try:
                    msg = json.loads(data.decode())
                except: continue 

                sender_ip = addr[0]
                if msg.get("peer_id") == self.peer_id: continue
                if msg.get("user") == self.username: continue

                msg_type = msg.get("type")
                
                if msg_type == "HELLO":
                    name = msg.get("user", "Unknown")
                    machine = msg.get("machine", "Unknown")
                    self.on_peer_found(f"{name} ({machine})", sender_ip)

            except Exception as e:
                print(f"Listen Error: {e}")