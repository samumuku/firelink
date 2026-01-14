import os
import sys
import json

# --- THEME COLORS ---
COLOR_ACCENT = "#D32F2F"       
COLOR_HOVER = "#FF5722"        
COLOR_PROGRESS = "#2CC985"     
COLOR_ERROR = "#C62828"        
COLOR_TEXT_LOGO = "#FF4500"    
COLOR_SIDEBAR = "#1a1a1a"      
COLOR_PAGE_BG = "#2b2b2b"      
COLOR_FRIENDS_BG = "#232323"   
COLOR_SCROLLBAR = "#8B0000"    

# --- PATHS ---
USER_CONFIG_FILE = os.path.join(os.path.expanduser("~"), "firelink_users.json")
BLOCKED_FILE = os.path.join(os.path.expanduser("~"), "firelink_blocked.json")

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# --- USER MANAGEMENT ---
def load_users():
    if os.path.exists(USER_CONFIG_FILE):
        try:
            with open(USER_CONFIG_FILE, "r") as f:
                return json.load(f)
        except: return []
    return []

def save_user(username):
    users = load_users()
    if username not in users:
        users.append(username)
        with open(USER_CONFIG_FILE, "w") as f:
            json.dump(users, f)

# --- BLOCKING SYSTEM ---
def load_blocked():
    """Returns a dict: {"192.168.1.5": "Mike"}"""
    if os.path.exists(BLOCKED_FILE):
        try:
            with open(BLOCKED_FILE, "r") as f:
                return json.load(f)
        except: return {}
    return {}

def block_user(ip, name):
    blocked = load_blocked()
    blocked[ip] = name
    with open(BLOCKED_FILE, "w") as f:
        json.dump(blocked, f)

def unblock_user(ip):
    blocked = load_blocked()
    if ip in blocked:
        del blocked[ip]
        with open(BLOCKED_FILE, "w") as f:
            json.dump(blocked, f)

def is_blocked(ip):
    blocked = load_blocked()
    return ip in blocked