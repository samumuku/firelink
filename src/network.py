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
        threading.Thread(target=self.broadcast_loop, daemon=True).start()
        threading.Thread(target=self.scan_loop, daemon=True).start()

    def get_smart_targets(self):
        """Returns specific broadcast addresses for Hamachi/VPNs"""
        targets = set()
        targets.add("255.255.255.255") # Global default
        
        try:
            # Detect Hamachi (25.x) or Radmin (26.x)
            hostname = socket.gethostname()
            local_ips = socket.gethostbyname_ex(hostname)[2]
            
            for ip in local_ips:
                if ip.startswith("25."):
                    targets.add("25.255.255.255") # Target ALL Hamachi users
                elif ip.startswith("26."):
                    targets.add("26.255.255.255") # Target ALL Radmin users
        except: pass
        
        return list(targets)

    def get_local_subnets(self):
        """Finds the base IP (e.g., 192.168.1) for standard LAN scanning"""
        subnets = []
        try:
            hostname = socket.gethostname()
            local_ips = socket.gethostbyname_ex(hostname)[2]
            for ip in local_ips:
                parts = ip.split('.')
                # Only scan standard LAN IPs (192.168.x / 172.x / 10.x)
                if len(parts) == 4 and parts[0] in ["192", "172", "10"]:
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

    def broadcast_loop(self):
        """Sends to Global + Hamachi Broadcast addresses"""
        while self.running:
            msg = {
                "type": "HELLO",
                "user": self.username,
                "machine": self.machine_name
            }
            
            # Send to 255.255.255.255 AND 25.255.255.255
            targets = self.get_smart_targets()
            for t in targets:
                self.send_packet(t, msg)
                
            time.sleep(3)

    def scan_loop(self):
        """Only scans LAN subnets (Hotspots/Home WiFi)"""
        while self.running:
            msg = {
                "type": "HELLO",
                "user": self.username,
                "machine": self.machine_name
            }
            
            subnets = self.get_local_subnets()
            for base_ip in subnets:
                for i in range(1, 255):
                    self.send_packet(f"{base_ip}.{i}", msg)
                    time.sleep(0.005) 
            
            time.sleep(10)

    def listen_loop(self):
        while self.running:
            try:
                data, addr = self.sock.recvfrom(4096)
                try: msg = json.loads(data.decode())
                except: continue 

                sender_ip = addr[0]
                if msg.get("peer_id") == self.peer_id: continue
                if msg.get("user") == self.username: continue

                msg_type = msg.get("type")
                
                if msg_type == "HELLO":
                    name = msg.get("user", "Unknown")
                    machine = msg.get("machine", "Unknown")
                    self.on_peer_found(f"{name} ({machine})", sender_ip)
                
                # ... (Handle other messages like CLIPBOARD/LOBBY here)

            except Exception as e:
                print(f"Listen Error: {e}")