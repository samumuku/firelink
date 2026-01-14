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
COLOR_SIDEBAR = "#1a1a1a"      # Nav Sidebar (Darkest)
COLOR_PAGE_BG = "#2b2b2b"      # Content Background
COLOR_FRIENDS_BG = "#232323"   # Friends List Background
COLOR_SCROLLBAR = "#8B0000"    

# --- HELPER: PATHS & CONFIG ---
CONFIG_FILE = os.path.join(os.path.expanduser("~"), "firelink_users.json")

print(f"Config file path: {CONFIG_FILE}")

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
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# --- FILE TRANSFER FEATURE ---
class TransferPage(ctk.CTkFrame):
    def __init__(self, master, username):
        super().__init__(master, fg_color=COLOR_PAGE_BG, corner_radius=0)
        self.my_name = username
        
        # --- LOGIC ---
        real_downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
        self.transfer_engine = file_transfer.FileTransfer(download_folder=real_downloads_path)
        self.transfer_engine.start_receiver(self.update_status, self.update_progress)

        self.selected_friend_ip = None
        self.known_friends = [] 

        # --- LAYOUT: SPLIT INTO FRIENDS LIST (Left) AND STATUS (Right) ---
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Friends Sidebar (Internal to this page)
        self.friends_frame = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color=COLOR_FRIENDS_BG)
        self.friends_frame.grid(row=0, column=0, sticky="nsew")
        
        ctk.CTkLabel(self.friends_frame, text="Online", font=("Arial", 14, "bold"), text_color="gray").pack(pady=(20, 10))
        
        self.friends_list = ctk.CTkScrollableFrame(self.friends_frame, width=180, fg_color="transparent",
                                                   scrollbar_button_color=COLOR_SCROLLBAR, scrollbar_button_hover_color=COLOR_HOVER)
        self.friends_list.pack(fill="both", expand=True, padx=10, pady=10)

        # Manual Connect Button (Small, at bottom of friends list)
        self.manual_btn = ctk.CTkButton(self.friends_frame, text="Manual IP", 
                                        height=25, fg_color="transparent", border_width=1, 
                                        text_color="gray", border_color="gray",
                                        command=self.manual_connect_dialog)
        self.manual_btn.pack(pady=20)

        # Main Action Area (Right Side)
        self.action_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.action_frame.grid(row=0, column=1, sticky="nsew")

        # Centering Content
        self.center_box = ctk.CTkFrame(self.action_frame, fg_color="transparent")
        self.center_box.place(relx=0.5, rely=0.5, anchor="center")

        self.status_label = ctk.CTkLabel(self.center_box, text="Looking for people...", font=("Arial", 24), text_color="#dce4e6")
        self.status_label.pack(pady=(0, 20))

        self.progressbar = ctk.CTkProgressBar(self.center_box, width=400, progress_color=COLOR_PROGRESS)
        self.progressbar.pack(pady=10)
        self.progressbar.set(0)
        
        self.pct_label = ctk.CTkLabel(self.center_box, text="0%", text_color="gray")
        self.pct_label.pack(pady=5)
        
        self.action_button = ctk.CTkButton(self.center_box, text="Select Friend First", state="disabled",
                                           fg_color=COLOR_ACCENT, hover_color=COLOR_HOVER, 
                                           font=("Arial", 16, "bold"), height=40,
                                           command=self.pick_and_send)
        self.action_button.pack(pady=30)

        # --- NETWORKING START ---
        self.discovery = network.PeerDiscovery(self.my_name, self.found_friend, None)
        self.discovery.start()

    # --- LOGIC METHODS ---
    def found_friend(self, name, ip):
        if ip not in self.known_friends:
            self.known_friends.append(ip)
            self.after(0, lambda: self.create_friend_button(name, ip))

    def create_friend_button(self, name, ip):
        # Show friend in the list with a green circle to show they're online
        display_text = f"🟢 {name}"
        # Create the button
        btn = ctk.CTkButton(self.friends_list, 
                    text=display_text, 
                    fg_color="transparent", 
                    border_width=1, 
                    border_color="#B22222", 
                    hover_color=COLOR_ACCENT, 
                    anchor="w",
                    command=lambda: self.select_friend(name, ip))
        btn.pack(pady=5, fill="x")
        btn.pack(pady=5, fill="x")
        
        # Create the menu
        context_menu = tk.Menu(self, tearoff=0, bg=COLOR_PAGE_BG, fg="white")
        context_menu.add_command(label="Ping User", command=lambda: print(f"Pinging {ip}..."))
        context_menu.add_command(label="Block", command=lambda: print(f"Blocking {name}"))
        
        # Bind Right Click
        def do_popup(event):
            try: context_menu.tk_popup(event.x_root, event.y_root)
            finally: context_menu.grab_release()

        btn.bind("<Button-3>", do_popup)

    # Connect manually to an IP address
    # --- This was implemented because for instance, the school PCs do not allow to receive broadcast packets, without admin rights.
    # --- So users can still connect directly if they know the IP of the target machine. But this method is not bidirectional.
    # --- Only works in a unprofessional network environment, such as home with friends.
    def manual_connect_dialog(self):
        ip = ctk.CTkInputDialog(text="Enter IP:", title="Direct Connect").get_input()
        if ip: self.select_friend(f"Ghost ({ip})", ip)

    # selecting the person to send the file(s) to
    def select_friend(self, name, ip):
        self.selected_friend_ip = ip # ip to send to
        self.status_label.configure(text=f"Linked with {name}")
        self.action_button.configure(state="normal", text="Send")

    # pick a file and then send it to the person we wish to send it to
    def pick_and_send(self):
        if not self.selected_friend_ip: return # pick someone first or disable button
        filename = filedialog.askopenfilename() # open file dialog(file window)
        if filename:
            self.transfer_engine.send_file(self.selected_friend_ip, filename, self.update_status, self.update_progress)

    # simply update the label text for the current transfer status
    def update_status(self, text):
        self.after(0, lambda: self.status_label.configure(text=text))

    # progress bar update, when receiving or sending
    def update_progress(self, val):
        self.after(0, lambda: self.progressbar.set(val))
        self.after(0, lambda: self.pct_label.configure(text=f"{int(val*100)}%"))


# --- GENERIC PLACEHOLDER PAGE ---
class PlaceholderPage(ctk.CTkFrame):
    def __init__(self, master, title):
        super().__init__(master, fg_color=COLOR_PAGE_BG, corner_radius=0)
        
        label = ctk.CTkLabel(self, text=title, font=("Arial", 30, "bold"), text_color="gray")
        label.place(relx=0.5, rely=0.5, anchor="center")
        
        sub = ctk.CTkLabel(self, text="Feature coming soon...", font=("Arial", 16), text_color="gray")
        sub.place(relx=0.5, rely=0.55, anchor="center")


# --- THE DASHBOARD (Nav Bar + Page Switcher) ---
class Dashboard(ctk.CTkFrame):
    def __init__(self, master, username):
        super().__init__(master, fg_color=COLOR_PAGE_BG)
        
        # Grid: Col 0 = Nav Sidebar, Col 1 = Page Content
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # --- 1. NAVIGATION SIDEBAR (Far Left) ---
        self.nav_bar = ctk.CTkFrame(self, width=140, corner_radius=0, fg_color=COLOR_SIDEBAR)
        self.nav_bar.grid(row=0, column=0, sticky="nsew")
        
        # Logo Area
        logo_path = resource_path(os.path.join("img", "logo.jpg"))
        if os.path.exists(logo_path):
            img_data = Image.open(logo_path)
            self.logo_img = ctk.CTkImage(img_data, img_data, size=(100, 60)) 
            ctk.CTkLabel(self.nav_bar, text="", image=self.logo_img).pack(pady=(30, 10))
        
        ctk.CTkLabel(self.nav_bar, text="FIRELINK", font=("Arial", 18, "bold"), text_color=COLOR_TEXT_LOGO).pack(pady=(0, 30))

        # Nav Buttons
        self.btn_transfer = self.create_nav_btn("Transfer", self.show_transfer)
        self.btn_test1 = self.create_nav_btn("Test 1", self.show_test1)
        self.btn_test2 = self.create_nav_btn("Test 2", self.show_test2)

        # User Profile (Bottom)
        self.user_lbl = ctk.CTkLabel(self.nav_bar, text=f"{username}", text_color="gray")
        self.user_lbl.pack(side="bottom", pady=20)

        # --- 2. MAIN CONTENT AREA ---
        self.content_area = ctk.CTkFrame(self, corner_radius=0, fg_color=COLOR_PAGE_BG)
        self.content_area.grid(row=0, column=1, sticky="nsew")
        self.content_area.grid_rowconfigure(0, weight=1)
        self.content_area.grid_columnconfigure(0, weight=1)

        # --- INITIALIZE PAGES ---
        # We create them all now so they keep running in background
        self.page_transfer = TransferPage(self.content_area, username)
        self.page_test1 = PlaceholderPage(self.content_area, "Future Module 1")
        self.page_test2 = PlaceholderPage(self.content_area, "Future Module 2")

        # Show default
        self.show_transfer()

    def create_nav_btn(self, text, command):
        btn = ctk.CTkButton(self.nav_bar, text=text, fg_color="transparent", 
                            text_color="lightgray", hover_color=COLOR_FRIENDS_BG, 
                            anchor="w", height=40, command=command)
        btn.pack(fill="x", padx=10, pady=5)
        return btn

    def show_transfer(self):
        self.highlight_btn(self.btn_transfer)
        self.show_frame(self.page_transfer)

    def show_test1(self):
        self.highlight_btn(self.btn_test1)
        self.show_frame(self.page_test1)

    def show_test2(self):
        self.highlight_btn(self.btn_test2)
        self.show_frame(self.page_test2)

    def show_frame(self, frame):
        # Hide all, show one
        self.page_transfer.grid_forget()
        self.page_test1.grid_forget()
        self.page_test2.grid_forget()
        frame.grid(row=0, column=0, sticky="nsew")

    def highlight_btn(self, active_btn):
        # Reset colors
        for btn in [self.btn_transfer, self.btn_test1, self.btn_test2]:
            btn.configure(fg_color="transparent", text_color="lightgray")
        # Highlight active
        active_btn.configure(fg_color=COLOR_ACCENT, text_color="white")


# --- AUTH FRAME (Unchanged) ---
class AuthFrame(ctk.CTkFrame):
    def __init__(self, master, on_login_success):
        super().__init__(master, fg_color=COLOR_PAGE_BG)
        self.on_login_success = on_login_success 
        self.center_box = ctk.CTkFrame(self, fg_color="transparent")
        self.center_box.place(relx=0.5, rely=0.5, anchor="center")

        logo_path = resource_path(os.path.join("img", "logo.jpg"))
        if os.path.exists(logo_path):
            img_data = Image.open(logo_path)
            self.logo_img = ctk.CTkImage(img_data, img_data, size=(250, 140))
            ctk.CTkLabel(self.center_box, text="", image=self.logo_img).pack(pady=10)

        ctk.CTkLabel(self.center_box, text="FIRELINK", font=("Arial", 32, "bold"), text_color=COLOR_TEXT_LOGO).pack(pady=(0, 30))
        
        # Mode Switch
        self.mode_frame = ctk.CTkFrame(self.center_box, fg_color="transparent")
        self.mode_frame.pack(pady=10)
        self.btn_mode_login = ctk.CTkButton(self.mode_frame, text="Login", width=100, fg_color=COLOR_ACCENT, command=self.show_login)
        self.btn_mode_login.pack(side="left", padx=5)
        self.btn_mode_register = ctk.CTkButton(self.mode_frame, text="Register", width=100, fg_color="transparent", border_width=1, border_color=COLOR_ACCENT, command=self.show_register)
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
        ctk.CTkButton(self.input_frame, text="Enter the Fire", width=220, fg_color=COLOR_ACCENT, hover_color=COLOR_HOVER, command=self.perform_login).pack(pady=15)

    def show_register(self):
        self.btn_mode_login.configure(fg_color="transparent")
        self.btn_mode_register.configure(fg_color=COLOR_ACCENT)
        for widget in self.input_frame.winfo_children(): widget.destroy()
        
        self.entry_widget = ctk.CTkEntry(self.input_frame, placeholder_text="New Username", width=220)
        self.entry_widget.pack(pady=5)
        ctk.CTkButton(self.input_frame, text="Create Profile", width=220, fg_color=COLOR_ACCENT, hover_color=COLOR_HOVER, command=self.perform_register).pack(pady=15)

    def perform_login(self):
        name = self.entry_widget.get()
        if name and name != "No profiles found": self.on_login_success(name)

    def perform_register(self):
        name = self.entry_widget.get()
        if name:
            save_user(name)
            self.on_login_success(name)


# --- ROOT APP ---
class FirelinkApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Firelink")
        self.geometry("1000x650") # Made wider for the nav bar
        self.resizable(False, False)

        try: ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)
        except: pass

        icon_path = resource_path(os.path.join("img", "fire.ico"))
        if os.path.exists(icon_path): self.iconbitmap(icon_path)

        self.current_frame = None
        self.show_auth()

    def show_auth(self):
        if self.current_frame: self.current_frame.destroy()
        self.current_frame = AuthFrame(self, self.start_dashboard)
        self.current_frame.pack(fill="both", expand=True)

    def start_dashboard(self, username):
        if self.current_frame: self.current_frame.destroy()
        # Switch to the new Dashboard (which holds the Transfer Page)
        self.current_frame = Dashboard(self, username)
        self.current_frame.pack(fill="both", expand=True)

if __name__ == "__main__":
    app = FirelinkApp()
    app.mainloop()