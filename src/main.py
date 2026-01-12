import customtkinter as ctk
import os
import sys
import json
import ctypes
from PIL import Image
from tkinter import filedialog
import network
import file_transfer

# --- CONFIGURATION ---
ctk.set_appearance_mode("Dark")

# --- FIRE THEME COLORS ---
COLOR_ACCENT = "#D32F2F"       
COLOR_HOVER = "#FF5722"        
COLOR_PROGRESS = "#FF8C00"     
COLOR_TEXT_LOGO = "#FF4500"    
COLOR_SIDEBAR = "#1a1a1a"      
COLOR_MAIN_BG = "#2b2b2b"      
COLOR_SCROLLBAR = "#8B0000"    

# --- HELPER: SAVE/LOAD USERS ---
# This saves the file to C:\Users\YourName\firelink_users.json
# This guarantees we have permission to write to it.
CONFIG_FILE = os.path.join(os.path.expanduser("~"), "firelink_users.json")

def load_users():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        except: return []
    return []

def save_user(username):
    users = load_users()
    if username not in users:
        users.append(username)
        with open(CONFIG_FILE, "w") as f:
            json.dump(users, f)

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

# --- SCREEN 1: THE WELCOME / AUTH PAGE ---
class AuthFrame(ctk.CTkFrame):
    def __init__(self, master, on_login_success):
        super().__init__(master, fg_color=COLOR_MAIN_BG)
        self.on_login_success = on_login_success 
        
        self.center_box = ctk.CTkFrame(self, fg_color="transparent")
        self.center_box.place(relx=0.5, rely=0.5, anchor="center")

        logo_path = resource_path(os.path.join("img", "logo.jpg"))
        if os.path.exists(logo_path):
            img_data = Image.open(logo_path)
            self.logo_img = ctk.CTkImage(img_data, img_data, size=(250, 140))
            ctk.CTkLabel(self.center_box, text="", image=self.logo_img).pack(pady=10)

        ctk.CTkLabel(self.center_box, text="FIRELINK", font=("Arial", 32, "bold"), 
                     text_color=COLOR_TEXT_LOGO).pack(pady=(0, 30))

        self.mode_frame = ctk.CTkFrame(self.center_box, fg_color="transparent")
        self.mode_frame.pack(pady=10)
        
        self.btn_mode_login = ctk.CTkButton(self.mode_frame, text="Login", width=100, 
                                            fg_color=COLOR_ACCENT, hover_color=COLOR_HOVER,
                                            command=self.show_login)
        self.btn_mode_login.pack(side="left", padx=5)
        
        self.btn_mode_register = ctk.CTkButton(self.mode_frame, text="Register", width=100,
                                               fg_color="transparent", border_width=1, border_color=COLOR_ACCENT,
                                               command=self.show_register)
        self.btn_mode_register.pack(side="left", padx=5)

        self.input_frame = ctk.CTkFrame(self.center_box, fg_color="transparent")
        self.input_frame.pack(pady=20)
        
        self.entry_widget = None 
        self.show_login() 

    def show_login(self):
        self.btn_mode_login.configure(fg_color=COLOR_ACCENT)
        self.btn_mode_register.configure(fg_color="transparent")
        
        for widget in self.input_frame.winfo_children(): widget.destroy()
        
        users = load_users()
        if not users: users = ["No profiles found"]
        
        self.entry_widget = ctk.CTkComboBox(self.input_frame, values=users, width=220)
        self.entry_widget.pack(pady=5)
        
        ctk.CTkButton(self.input_frame, text="Enter the Fire", width=220, 
                      fg_color=COLOR_ACCENT, hover_color=COLOR_HOVER,
                      command=self.perform_login).pack(pady=15)

    def show_register(self):
        self.btn_mode_login.configure(fg_color="transparent")
        self.btn_mode_register.configure(fg_color=COLOR_ACCENT)
        
        for widget in self.input_frame.winfo_children(): widget.destroy()
        
        self.entry_widget = ctk.CTkEntry(self.input_frame, placeholder_text="New Username", width=220)
        self.entry_widget.pack(pady=5)
        
        ctk.CTkButton(self.input_frame, text="Create Profile", width=220, 
                      fg_color=COLOR_ACCENT, hover_color=COLOR_HOVER,
                      command=self.perform_register).pack(pady=15)

    def perform_login(self):
        name = self.entry_widget.get()
        if name and name != "No profiles found":
            self.on_login_success(name)

    def perform_register(self):
        name = self.entry_widget.get()
        if name:
            save_user(name)
            self.on_login_success(name)


class MainInterfaceFrame(ctk.CTkFrame):
    def __init__(self, master, username):
        super().__init__(master, fg_color=COLOR_MAIN_BG)
        self.my_name = username

        # --- SETUP FILE TRANSFER ENGINE ---
        # Get the real system Downloads folder
        real_downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
        
        self.transfer_engine = file_transfer.FileTransfer(download_folder=real_downloads_path)
        self.transfer_engine.start_receiver(self.update_status, self.update_progress)
        
        # 1. Grid Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- SIDEBAR ---
        self.sidebar = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color=COLOR_SIDEBAR)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        
        # Load Logo
        logo_path = resource_path(os.path.join("img", "logo.jpg"))
        if os.path.exists(logo_path):
            img_data = Image.open(logo_path)
            self.logo_img = ctk.CTkImage(img_data, img_data, size=(180, 100)) 
            ctk.CTkLabel(self.sidebar, text="", image=self.logo_img).grid(row=0, column=0, padx=20, pady=(20,0))

        ctk.CTkLabel(self.sidebar, text="FIRELINK", font=("Arial", 24, "bold"), text_color=COLOR_TEXT_LOGO).grid(row=1, column=0, pady=(5, 20))
        
        self.user_card = ctk.CTkFrame(self.sidebar, fg_color="#333", corner_radius=5)
        self.user_card.grid(row=2, column=0, padx=10, pady=(0,20), sticky="ew")
        ctk.CTkLabel(self.user_card, text=f"Logged in as:\n{self.my_name}", text_color="gray").pack(pady=5)

        ctk.CTkLabel(self.sidebar, text="Available:", text_color="gray").grid(row=3, column=0, padx=20, pady=5)

        self.friends_list = ctk.CTkScrollableFrame(self.sidebar, width=180, height=250, fg_color="transparent",
                                                   scrollbar_button_color=COLOR_SCROLLBAR, scrollbar_button_hover_color=COLOR_HOVER)
        self.friends_list.grid(row=4, column=0, padx=20, pady=5)
        
        # --- NEW: MANUAL CONNECT BUTTON ---
        # If firewall blocks discovery, use this to force a connection
        self.manual_btn = ctk.CTkButton(self.sidebar, text="Manual Connect (IP)", 
                                        height=30, fg_color="transparent", border_width=1, 
                                        text_color="gray", border_color="gray",
                                        command=self.manual_connect_dialog)
        self.manual_btn.grid(row=5, column=0, padx=20, pady=20)

        # --- MAIN AREA ---
        self.main_area = ctk.CTkFrame(self, corner_radius=0, fg_color=COLOR_MAIN_BG)
        self.main_area.grid(row=0, column=1, sticky="nsew")

        self.status_label = ctk.CTkLabel(self.main_area, text="Finding items to send", font=("Arial", 24), text_color="#dce4e6")
        self.status_label.pack(pady=(150, 20))

        self.progressbar = ctk.CTkProgressBar(self.main_area, width=400, progress_color=COLOR_PROGRESS)
        self.progressbar.pack(pady=10)
        self.progressbar.set(0)
        
        self.pct_label = ctk.CTkLabel(self.main_area, text="0%", text_color="gray")
        self.pct_label.pack(pady=5)
        
        self.action_button = ctk.CTkButton(self.main_area, text="Select Friend First", state="disabled",
                                           fg_color=COLOR_ACCENT, hover_color=COLOR_HOVER, 
                                           command=self.pick_and_send)
        self.action_button.pack(pady=20)

        # --- NETWORKING ---
        self.selected_friend_ip = None
        self.known_friends = [] 
        self.discovery = network.PeerDiscovery(self.my_name, self.found_friend, None)
        self.discovery.start()

    def found_friend(self, name, ip):
        if ip not in self.known_friends:
            self.known_friends.append(ip)
            self.after(0, lambda: self.create_friend_button(name, ip))

    def create_friend_button(self, name, ip):
        btn = ctk.CTkButton(self.friends_list, text=f"{name}", fg_color="transparent", 
                            border_width=1, border_color="#B22222", hover_color=COLOR_ACCENT, 
                            command=lambda: self.select_friend(name, ip))
        btn.pack(pady=5, fill="x")

    def manual_connect_dialog(self):
        """Ask for IP manually if the firewall blocks discovery"""
        ip = ctk.CTkInputDialog(text="Enter friend's IP Address:", title="Direct Connect").get_input()
        if ip:
            # We add them as a "Ghost" friend
            self.select_friend(f"Ghost ({ip})", ip)

    def select_friend(self, name, ip):
        self.selected_friend_ip = ip
        self.status_label.configure(text=f"Linked with {name}")
        self.action_button.configure(state="normal", text="Select file(s) to send")

    def pick_and_send(self):
        if not self.selected_friend_ip: return
        filename = filedialog.askopenfilename()
        if filename:
            self.transfer_engine.send_file(
                self.selected_friend_ip, 
                filename, 
                self.update_status, 
                self.update_progress
            )

    def update_status(self, text):
        self.after(0, lambda: self.status_label.configure(text=text))

    def update_progress(self, val):
        self.after(0, lambda: self.progressbar.set(val))
        self.after(0, lambda: self.pct_label.configure(text=f"{int(val*100)}%"))
        
# --- ROOT APP ---
class FirelinkApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Firelink")
        self.geometry("900x600")
        self.resizable(False, False)
        
        # --- PREVENT WINDOWS FROM SLEEPING THIS APP ---
        # This tells Windows: "ES_CONTINUOUS | ES_SYSTEM_REQUIRED"
        # It forces the OS to keep the background threads (networking) running at full speed.
        try:
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)
        except Exception as e:
            print(f"Could not set execution state: {e}")

        icon_path = resource_path(os.path.join("img", "fire.ico"))
        if os.path.exists(icon_path): self.iconbitmap(icon_path)

        self.current_frame = None
        self.show_auth()

    def show_auth(self):
        if self.current_frame: self.current_frame.destroy()
        self.current_frame = AuthFrame(self, self.start_app)
        self.current_frame.pack(fill="both", expand=True)

    def start_app(self, username):
        if self.current_frame: self.current_frame.destroy()
        self.current_frame = MainInterfaceFrame(self, username)
        self.current_frame.pack(fill="both", expand=True)

if __name__ == "__main__":
    app = FirelinkApp()
    app.mainloop()