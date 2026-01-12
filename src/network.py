import socket
import threading
import time

# --- CONFIGURATION ---
BROADCAST_IP = "255.255.255.255" # Address that means "Everyone"
DISCOVERY_PORT = 12345           # The channel we shout on

class PeerDiscovery:
    def __init__(self, username, on_peer_found_callback):
        self.username = username
        self.callback = on_peer_found_callback
        self.running = True
        
        # 1. Setup the UDP Socket (The Radio)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # Allow reusing the port (so you can test with 2 apps on 1 PC)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        # Enable Broadcasting
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        
        # Bind to the port to listen
        self.sock.bind(("", DISCOVERY_PORT))

    def start(self):
        """Starts the Ear and the Mouth in background threads"""
        threading.Thread(target=self.listen_loop, daemon=True).start()
        threading.Thread(target=self.broadcast_loop, daemon=True).start()

    def broadcast_loop(self):
        """The Mouth: Shouts 'I am here' every 3 seconds"""
        while self.running:
            msg = f"HELLO|{self.username}"
            try:
                self.sock.sendto(msg.encode(), (BROADCAST_IP, DISCOVERY_PORT))
            except Exception as e:
                print(f"Broadcast Error: {e}")
            time.sleep(3)

    def listen_loop(self):
        """The Ear: Listens for others"""
        while self.running:
            try:
                data, addr = self.sock.recvfrom(1024)
                ip = addr[0]
                
                # Decode message: "HELLO|Mike"
                msg = data.decode().split("|")
                
                if len(msg) >= 2 and msg[0] == "HELLO":
                    friend_name = msg[1]
                    
                    # Don't add yourself to the list
                    # (We check if the name is NOT my own name)
                    if friend_name != self.username:
                        # Call the GUI function to add the button
                        self.callback(friend_name, ip)
                        
            except Exception as e:
                print(f"Listen Error: {e}")