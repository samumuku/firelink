import socket
import threading
import subprocess
import re
import os
import platform

class NetworkScanner:
    def __init__(self):
        self.active_devices = [] # List of dicts: {"ip": "...", "mac": "...", "hostname": "..."}
        self.lock = threading.Lock()
        
    def get_my_ip(self):
        """Finds local IP to determine the subnet (e.g. 192.168.1.x)"""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # Connect to a public DNS (doesn't send data) to get our local interface IP
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        except Exception:
            ip = "127.0.0.1"
        finally:
            s.close()
        return ip

    def get_default_gateway(self):
        """Tries to guess the router IP for the Admin Button"""
        # Quick and dirty: usually the .1 of the subnet
        my_ip = self.get_my_ip()
        if my_ip == "127.0.0.1": return None
        
        parts = my_ip.split(".")
        return f"{parts[0]}.{parts[1]}.{parts[2]}.1"

    def start_scan(self, on_device_found, on_finished):
        """Starts the scan in a background thread"""
        threading.Thread(target=self._scan_thread, args=(on_device_found, on_finished), daemon=True).start()

    def _scan_thread(self, on_device_found, on_finished):
        my_ip = self.get_my_ip()
        base_ip = ".".join(my_ip.split(".")[:-1]) # e.g., "192.168.1"
        
        # 1. Ping Sweep (Wake up devices)
        threads = []
        for i in range(1, 255):
            target = f"{base_ip}.{i}"
            t = threading.Thread(target=self._ping_host, args=(target,))
            threads.append(t)
            t.start()
            
        # Wait for all pings to finish
        for t in threads:
            t.join()
            
        # 2. Read ARP Table (Get MACs)
        # Pinging them forced the OS to resolve their MAC addresses. Now we read the cache.
        self._parse_arp_table(base_ip, on_device_found)
        
        on_finished()

    def _ping_host(self, ip):
        """Pings a single host silently"""
        param = '-n' if platform.system().lower() == 'windows' else '-c'
        # Timeout 1s, 1 packet
        cmd = ['ping', param, '1', ip]
        # Hide output
        subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def _parse_arp_table(self, base_ip_filter, callback):
        """Runs 'arp -a' and parses the output"""
        try:
            output = subprocess.check_output("arp -a", shell=True).decode(errors="ignore")
            
            # Regex to find IP and MAC addresses
            # Looks for:  192.168.1.5   ab-cd-ef-12-34-56
            entries = re.findall(r"(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\s+([-0-9a-fA-F]{17})", output)
            
            seen_ips = set()
            
            for ip, mac in entries:
                if base_ip_filter in ip and ip not in seen_ips:
                    # Try to get hostname (slow, so maybe skip or do async if too laggy)
                    try:
                        hostname = socket.gethostbyaddr(ip)[0]
                    except:
                        hostname = "Unknown Device"
                    
                    device = {"ip": ip, "mac": mac, "name": hostname}
                    callback(device)
                    seen_ips.add(ip)

        except Exception as e:
            print(f"ARP Error: {e}")