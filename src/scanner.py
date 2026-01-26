import socket
import threading
import subprocess
import re
import os
import platform

class NetworkScanner:
    def __init__(self):
        self.active_devices = [] 
        self.lock = threading.Lock()
        self.system = platform.system().lower() # 'windows' or 'darwin'
        
        # --- LITE VENDOR DATABASE (Common Home Devices) ---
        # These are the "prefixes" of MAC addresses that identify the brand.
        self.vendors = {
            # Apple (Common OUIs)
            "00:D8:61": "Apple", "AC:BC:32": "Apple", "A4:83:E7": "Apple", 
            "28:CF:E9": "Apple", "00:1C:B3": "Apple", "00:26:08": "Apple",
            
            # Samsung
            "00:12:47": "Samsung", "00:15:B9": "Samsung", "A0:21:95": "Samsung",
            
            # Routers / Networking
            "00:1A:2B": "TP-Link", "18:A6:F7": "TP-Link",
            "00:09:5B": "Netgear", "C4:04:15": "Netgear",
            "18:31:BF": "ASUS",    "2C:54:2D": "ASUS",
            "C0:25:E9": "TP-Link",
            
            # PC Chips (Ethernet/WiFi cards in laptops)
            "00:1B:21": "Intel",   "00:21:6A": "Intel",
            "00:E0:4C": "Realtek", "54:04:A6": "Realtek",
            
            # IoT / Smart Home
            "DC:A6:32": "Raspberry Pi", "B8:27:EB": "Raspberry Pi", "D8:3A:DD": "Raspberry Pi",
            "5C:CF:7F": "Espressif (Smart Bulb/Plug)", "60:01:94": "Espressif (Smart Bulb/Plug)",
            "A4:7B:9D": "Espressif (Smart Bulb/Plug)",
            
            # Consoles
            "44:94:FC": "Sony (PlayStation)", "00:04:1F": "Sony (PlayStation)",
            "50:E5:49": "Microsoft (Xbox)",   "48:2C:6A": "HP",
            "98:B6:E9": "Nintendo Switch"
        }

    def get_vendor(self, mac):
        """Identifies manufacturer from MAC address"""
        # Clean the mac: "A1:B2:C3..." -> "A1:B2:C3"
        clean_mac = mac.upper().replace("-", ":")
        
        # 1. Check the first 8 chars (XX:XX:XX)
        if len(clean_mac) >= 8:
            prefix = clean_mac[:8] # Get the OUI part
            if prefix in self.vendors:
                return self.vendors[prefix]
        
        # 2. Check for Virtual Machines (Common specific prefixes)
        if clean_mac.startswith("00:50:56") or clean_mac.startswith("00:0C:29"):
            return "VMware"
        if clean_mac.startswith("00:15:5D"):
            return "Hyper-V"
            
        return "Unknown Device"

    def get_my_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
        except Exception:
            ip = "127.0.0.1"
        finally:
            s.close()
        return ip

    def get_default_gateway(self):
        my_ip = self.get_my_ip()
        if my_ip == "127.0.0.1": return None
        parts = my_ip.split(".")
        return f"{parts[0]}.{parts[1]}.{parts[2]}.1"

    def start_scan(self, on_device_found, on_finished):
        threading.Thread(target=self._scan_thread, args=(on_device_found, on_finished), daemon=True).start()

    def _scan_thread(self, on_device_found, on_finished):
        my_ip = self.get_my_ip()
        base_ip = ".".join(my_ip.split(".")[:-1]) 
        
        # 1. Ping Sweep
        threads = []
        batch_size = 50 
        
        for i in range(1, 255):
            target = f"{base_ip}.{i}"
            t = threading.Thread(target=self._ping_host, args=(target,))
            threads.append(t)
            t.start()
            
            if len(threads) >= batch_size:
                for t in threads: t.join()
                threads = []

        for t in threads: t.join()
            
        # 2. Read ARP Table
        self._parse_arp_table(base_ip, on_device_found)
        
        on_finished()

    def _ping_host(self, ip):
        # Cross-platform ping
        if self.system == "windows":
            cmd = ['ping', '-n', '1', '-w', '200', ip]
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, startupinfo=startupinfo)
        else:
            # macOS
            cmd = ['ping', '-c', '1', '-W', '200', ip]
            subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def send_wol(self, mac_address):
        """Sends a Magic Packet to wake up the specified MAC address"""
        try:
            # 1. Clean the MAC address
            clean_mac = mac_address.replace(":", "").replace("-", "")
            if len(clean_mac) != 12:
                print(f"Invalid MAC: {mac_address}")
                return False

            # 2. Build the Magic Packet
            data = bytes.fromhex("FF" * 6 + clean_mac * 16)
            
            # 3. Determine Broadcast Addresses
            # We want to send to 255.255.255.255 AND 192.168.1.255 (Subnet broadcast)
            targets = ["255.255.255.255"]
            try:
                my_ip = self.get_my_ip()
                if my_ip != "127.0.0.1":
                    # Assumes a standard home network (/24 subnet)
                    parts = my_ip.split(".")
                    subnet_broadcast = f"{parts[0]}.{parts[1]}.{parts[2]}.255"
                    targets.append(subnet_broadcast)
            except: pass

            # 4. Blast the packet
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                
                for target_ip in targets:
                    for port in [7, 9]: # Try both standard WoL ports
                        try:
                            sock.sendto(data, (target_ip, port))
                        except Exception as e:
                            print(f"Failed to send to {target_ip}:{port} - {e}")
            
            return True
        except Exception as e:
            print(f"WoL Critical Error: {e}")
            return False

    def _parse_arp_table(self, base_ip_filter, callback):
        try:
            output = subprocess.check_output("arp -a", shell=True).decode(errors="ignore")
            # Regex captures IP and MAC
            pattern = r"(?:\? \()?(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(?:\))?.*?\s+([-0-9a-fA-F:]{8,17})"
            entries = re.findall(pattern, output)
            seen_ips = set()
            
            for ip, mac in entries:
                if ip.endswith(".255") or ip == "224.0.0.251": continue
                
                mac_clean = mac.replace("-", ":").upper()

                if base_ip_filter in ip and ip not in seen_ips:
                    # Priority 1: Vendor Lookup (More reliable than hostname on modern networks)
                    vendor = self.get_vendor(mac_clean)
                    
                    # Priority 2: Hostname (if Vendor is Unknown)
                    if vendor == "Unknown Device":
                        try:
                            hostname = socket.gethostbyaddr(ip)[0]
                            if "." in hostname: hostname = hostname.split(".")[0]
                            vendor = hostname # Use hostname as the "Name"
                        except:
                            pass
                    
                    device = {"ip": ip, "mac": mac_clean, "name": vendor}
                    callback(device)
                    seen_ips.add(ip)

        except Exception as e:
            print(f"ARP Error: {e}")