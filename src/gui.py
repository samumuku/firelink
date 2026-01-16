import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog
from PIL import Image, ImageDraw
import os
import threading
import subprocess

# fichiers
import utils
import network
import file_transfer


# --- CS2 LINEUP DATABASE ---
# # Grouping: Map -> Lineup Name -> Data
# LINEUP_DATA = {
#     "Mirage": {
#         "[SMOKE] A Stairs": {
#             "type": "Smoke",
#             "desc": "jumpthrow",
#             "img": ["Mirage/A-Stairs/step1.jpg", "Mirage/A-Stairs/jumpthrow.jpg"]
#         },
#         "[SMOKE] A Jungle": {
#             "type": "Smoke",
#             "desc": "Jumpthrow",
#             "img": ["Mirage/Jungle/step1.jpg", "Mirage/Jungle/step2.jpg"]
#         },
#         "[SMOKE] Window (Bin Spawn)": {
#             "type": "Smoke",
#             "desc": "Hold D and jump throw",
#             "img": ["Mirage/Window/step1.jpg", "Mirage/Window/d_and_jumpthrow.jpg"]
#         },
#         "[SMOKE] Mid Short (spawn)": {
#             "type": "Smoke",
#             "desc": "jumpthrow",
#             "img": ["Mirage/Short/step1.jpg", "Mirage/Short/jumpthrow.jpg"]
#         },
#         "[SMOKE] Mid Connector (spawn)": {
#             "type": "Smoke",
#             "desc": "On the bin, crouch and then jumpthrow",
#             "img": ["Mirage/Connector/step1.jpg", "Mirage/Connector/crouch_jumpthrow.jpg"]
#         },
#         "[SMOKE] Ticket": {
#             "type": "Smoke",
#             "desc": "jumpthrow",
#             "img": ["Mirage/CtSpawn/step1.jpg", "Mirage/CtSpawn/step2.jpg"]
#         },
#         "[FLASH] CT to site flash (spawn)": {
#             "type": "Flash",
#             "desc": "Flash on site. Regular throw",
#             "img": ["Mirage/FlashSiteA-CT/step1.jpg", "Mirage/FlashSiteA-CT/regular_throw.jpg"]
#         },
#     },
#     "Inferno": {
#         "[MOLY] B Banana (Car)": {
#             "type": "Molly",
#             "desc": "1. Stand on the logs at the bottom of Banana.\n2. Aim at the top of the antenna.\n3. Run forward slightly and Left-click throw.",
#             "img": ["inferno_car.png"]
#         }
#     },
#     "Dust 2": {
#         "[SMOKE] Xbox (Mid)": {
#             "type": "Smoke",
#             "desc": "1. T Spawn, hug the wall near Suicided.\n2. Aim at the small dark dot on the wall across mid doors.\n3. Jump throw.",
#             "img": ["dust2_xbox.png"]
#         }
#     },
#     "Anubis": {},
#     "Ancient": {},
#     "Train": {}
# }

# --- POPUP NOTIFICATION ---
class NotificationPopup(ctk.CTkFrame):
    def __init__(self, master, message, is_error=False):
        color = utils.COLOR_ERROR if is_error else utils.COLOR_PROGRESS
        super().__init__(master, fg_color=color, corner_radius=10)
        
        symbol = "✖" if is_error else "✔"
        self.lbl = ctk.CTkLabel(self, text=f"{symbol}  {message}", font=("Arial", 14, "bold"), text_color="white")
        self.lbl.pack(padx=20, pady=10)
        
        self.place(relx=0.98, rely=0.95, anchor="se")
        self.after(3000, self.destroy)

# --- PAGE 1: SETTINGS (BLOCKED USERS) ---
class SettingsPage(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=utils.COLOR_PAGE_BG, corner_radius=0)
        
        # Header
        ctk.CTkLabel(self, text="Settings & Privacy", font=("Arial", 24, "bold"), text_color="white").pack(pady=30, anchor="w", padx=40)
        
        # Blocked List Section
        ctk.CTkLabel(self, text="Blocked Users", font=("Arial", 18, "bold"), text_color="gray").pack(pady=(10, 5), anchor="w", padx=40)
        
        self.blocked_list_frame = ctk.CTkScrollableFrame(self, height=300, fg_color=utils.COLOR_FRIENDS_BG)
        self.blocked_list_frame.pack(fill="x", padx=40, pady=10)
        
        self.refresh_blocked_list()

    def refresh_blocked_list(self):
        # Clear current list
        for widget in self.blocked_list_frame.winfo_children():
            widget.destroy()

        blocked = utils.load_blocked()
        
        if not blocked:
            ctk.CTkLabel(self.blocked_list_frame, text="No blocked users.", text_color="gray").pack(pady=20)
            return

        for ip, name in blocked.items():
            row = ctk.CTkFrame(self.blocked_list_frame, fg_color="transparent")
            row.pack(fill="x", pady=5)
            
            ctk.CTkLabel(row, text=f"{name} ({ip})", font=("Arial", 14), text_color="white").pack(side="left", padx=10)
            
            ctk.CTkButton(row, text="Unblock", width=80, fg_color=utils.COLOR_ACCENT, 
                          command=lambda i=ip: self.perform_unblock(i)).pack(side="right", padx=10)

    def perform_unblock(self, ip):
        utils.unblock_user(ip)
        self.refresh_blocked_list()

# --- PAGE 2: TRANSFER (MAIN) ---
class TransferPage(ctk.CTkFrame):
    def __init__(self, master, username):
        super().__init__(master, fg_color=utils.COLOR_PAGE_BG, corner_radius=0)
        self.my_name = username
        
        # Logic
        real_downloads_path = os.path.join(os.path.expanduser("~"), "Downloads")
        self.transfer_engine = file_transfer.FileTransfer(download_folder=real_downloads_path)
        self.transfer_engine.start_receiver(self.update_status, self.update_progress)

        self.selected_friend_ip = None
        self.friend_widgets = {} # Maps IP -> Button Widget

        # Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.friends_frame = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color=utils.COLOR_FRIENDS_BG)
        self.friends_frame.grid(row=0, column=0, sticky="nsew")
        
        ctk.CTkLabel(self.friends_frame, text="Online", font=("Arial", 14, "bold"), text_color="gray").pack(pady=(20, 10))
        
        self.friends_list = ctk.CTkScrollableFrame(self.friends_frame, width=180, fg_color="transparent")
        self.friends_list.pack(fill="both", expand=True, padx=10, pady=10)

        self.manual_btn = ctk.CTkButton(self.friends_frame, text="Manual IP", height=25, fg_color="transparent", 
                                        border_width=1, text_color="gray", border_color="gray", command=self.manual_connect_dialog)
        self.manual_btn.pack(pady=20)

        # Main Action Area
        self.action_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.action_frame.grid(row=0, column=1, sticky="nsew")

        self.center_box = ctk.CTkFrame(self.action_frame, fg_color="transparent")
        self.center_box.place(relx=0.5, rely=0.5, anchor="center")

        self.status_label = ctk.CTkLabel(self.center_box, text="Looking for people...", font=("Arial", 24), text_color="#dce4e6")
        self.status_label.pack(pady=(0, 20))

        self.progressbar = ctk.CTkProgressBar(self.center_box, width=400, progress_color=utils.COLOR_PROGRESS)
        self.progressbar.pack(pady=10)
        self.progressbar.set(0)
        
        self.pct_label = ctk.CTkLabel(self.center_box, text="0%", text_color="gray")
        self.pct_label.pack(pady=5)
        
        self.action_button = ctk.CTkButton(self.center_box, text="Select Friend First", state="disabled",
                                           fg_color=utils.COLOR_ACCENT, hover_color=utils.COLOR_HOVER, 
                                           font=("Arial", 16, "bold"), height=40, command=self.pick_and_send)
        self.action_button.pack(pady=30)

        # Network
        self.discovery = network.PeerDiscovery(self.my_name, self.found_friend, None)
        self.discovery.start()

    def found_friend(self, name, ip):
        # 1. Check if Blocked
        if utils.is_blocked(ip):
            return # Ignore them completely
            
        # 2. Check if already known
        if ip not in self.friend_widgets:
            self.after(0, lambda: self.create_friend_button(name, ip))

    def create_friend_button(self, name, ip):
        if ip in self.friend_widgets: return

        icon = self.get_status_icon()
        btn = ctk.CTkButton(self.friends_list, text=f"  {name}", image=icon, compound="left",
                            fg_color="transparent", border_width=1, border_color="#B22222", 
                            hover_color=utils.COLOR_ACCENT, anchor="w",
                            command=lambda: self.select_friend(name, ip))
        btn.pack(pady=5, fill="x")
        
        # Store widget reference
        self.friend_widgets[ip] = btn

        # Context Menu
        context_menu = tk.Menu(self, tearoff=0, bg=utils.COLOR_PAGE_BG, fg="white")
        context_menu.add_command(label="Ping User", command=lambda: self.ping_user(ip, name))
        context_menu.add_command(label="Block User", command=lambda: self.block_user_action(ip, name))
        
        def do_popup(event):
            try: context_menu.tk_popup(event.x_root, event.y_root)
            finally: context_menu.grab_release()

        btn.bind("<Button-3>", do_popup)

    def block_user_action(self, ip, name):
        utils.block_user(ip, name)
        # Remove button from UI immediately
        if ip in self.friend_widgets:
            self.friend_widgets[ip].destroy()
            del self.friend_widgets[ip]
        self.show_notification(f"Blocked {name}", is_error=True)

    def show_notification(self, message, is_error=False):
        root = self.winfo_toplevel()
        NotificationPopup(root, message, is_error)

    def ping_user(self, ip, name):
        threading.Thread(target=self._run_ping, args=(ip, name), daemon=True).start()
        self.show_notification(f"Pinging {name}...", is_error=False)

    def _run_ping(self, ip, name):
        try:
            param = '-n' if os.name == 'nt' else '-c'
            response = subprocess.run(['ping', param, '1', ip], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if response.returncode == 0:
                self.after(0, lambda: self.show_notification(f"{name} is reachable!", False))
            else:
                self.after(0, lambda: self.show_notification(f"{name} is unreachable.", True))
        except Exception as e:
            self.after(0, lambda: self.show_notification(f"Ping Error", True))

    def manual_connect_dialog(self):
        ip = ctk.CTkInputDialog(text="Enter IP:", title="Direct Connect").get_input()
        if ip: self.select_friend(f"Ghost ({ip})", ip)

    def select_friend(self, name, ip):
        self.selected_friend_ip = ip
        self.status_label.configure(text=f"Linked with {name}")
        self.action_button.configure(state="normal", text="Send")

    def pick_and_send(self):
        if not self.selected_friend_ip: return
        filename = filedialog.askopenfilename()
        if filename:
            self.transfer_engine.send_file(self.selected_friend_ip, filename, self.update_status, self.update_progress)

    def update_status(self, text):
        self.after(0, lambda: self.status_label.configure(text=text))

    def update_progress(self, val):
        self.after(0, lambda: self.progressbar.set(val))
        self.after(0, lambda: self.pct_label.configure(text=f"{int(val*100)}%"))

    def get_status_icon(self):
        size = (15, 15)
        img = Image.new("RGBA", size, (0, 0, 0, 0)) 
        draw = ImageDraw.Draw(img)
        draw.ellipse((1, 1, 13, 13), fill=utils.COLOR_PROGRESS) 
        return ctk.CTkImage(img, img, size=size)

# --- DASHBOARD ---
class Dashboard(ctk.CTkFrame):
    def __init__(self, master, username):
        super().__init__(master, fg_color=utils.COLOR_PAGE_BG)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.nav_bar = ctk.CTkFrame(self, width=140, corner_radius=0, fg_color=utils.COLOR_SIDEBAR)
        self.nav_bar.grid(row=0, column=0, sticky="nsew")
        
        # Logo
        logo_path = utils.resource_path(os.path.join("img", "logo.jpg"))
        if os.path.exists(logo_path):
            img_data = Image.open(logo_path)
            self.logo_img = ctk.CTkImage(img_data, img_data, size=(100, 60)) 
            ctk.CTkLabel(self.nav_bar, text="", image=self.logo_img).pack(pady=(30, 10))
        
        ctk.CTkLabel(self.nav_bar, text="FIRELINK", font=("Arial", 18, "bold"), text_color=utils.COLOR_TEXT_LOGO).pack(pady=(0, 30))

        # Nav Buttons
        self.btn_transfer = self.create_nav_btn("Transfer", self.show_transfer)
        #self.btn_lineups = self.create_nav_btn("CS2 Lineups", self.show_lineups)
        
        # --- USER PROFILE GROUP (Bottom) ---
        # Container to hold Settings + Username side-by-side
        self.user_frame = ctk.CTkFrame(self.nav_bar, fg_color="transparent")
        self.user_frame.pack(side="bottom", fill="x", pady=20, padx=10)

        # Settings Button (Small Icon on the Left)
        self.btn_settings = ctk.CTkButton(self.user_frame, text="⚙", width=30, height=30,
                                          fg_color="transparent", hover_color=utils.COLOR_FRIENDS_BG,
                                          text_color="gray", font=("Arial", 20),
                                          command=self.show_settings)
        self.btn_settings.pack(side="left")

        # Username Label (Next to it)
        display_name = (username[:10] + '..') if len(username) > 12 else username
        self.user_lbl = ctk.CTkLabel(self.user_frame, text=display_name, text_color="gray", font=("Arial", 12, "bold"))
        self.user_lbl.pack(side="left", padx=10)

        # Content Area
        self.content_area = ctk.CTkFrame(self, corner_radius=0, fg_color=utils.COLOR_PAGE_BG)
        self.content_area.grid(row=0, column=1, sticky="nsew")
        self.content_area.grid_rowconfigure(0, weight=1)
        self.content_area.grid_columnconfigure(0, weight=1)

        # Pages
        self.page_transfer = TransferPage(self.content_area, username)
        self.page_settings = SettingsPage(self.content_area)
        self.page_lineups = LineupPage(self.content_area)

        self.show_transfer()

    def create_nav_btn(self, text, command):
        btn = ctk.CTkButton(self.nav_bar, text=text, fg_color="transparent", 
                            text_color="lightgray", hover_color=utils.COLOR_FRIENDS_BG, 
                            anchor="w", height=40, command=command)
        btn.pack(fill="x", padx=10, pady=5)
        return btn

    def show_transfer(self):
        self.highlight_btn(self.btn_transfer)
        self.show_frame(self.page_transfer)
        
    def show_lineups(self):
        self.highlight_btn(self.btn_lineups)
        self.show_frame(self.page_lineups)

    def show_settings(self):
        # Refresh the list every time we open settings
        self.page_settings.refresh_blocked_list()
        self.highlight_btn(self.btn_settings)
        self.show_frame(self.page_settings)

    def show_frame(self, frame):
        self.page_transfer.grid_forget()
        self.page_settings.grid_forget()
        frame.grid(row=0, column=0, sticky="nsew")

    def highlight_btn(self, active_btn):
        for btn in [self.btn_transfer, self.btn_settings]:
            btn.configure(fg_color="transparent", text_color="lightgray")
        # Note: If settings is active, we color the text/icon
        if active_btn == self.btn_settings:
            active_btn.configure(text_color=utils.COLOR_ACCENT)
        else:
            active_btn.configure(fg_color=utils.COLOR_ACCENT, text_color="white")

# --- AUTH FRAME ---
class AuthFrame(ctk.CTkFrame):
    def __init__(self, master, on_login_success):
        super().__init__(master, fg_color=utils.COLOR_PAGE_BG)
        self.on_login_success = on_login_success 
        self.center_box = ctk.CTkFrame(self, fg_color="transparent")
        self.center_box.place(relx=0.5, rely=0.5, anchor="center")

        logo_path = utils.resource_path(os.path.join("img", "logo.jpg"))
        if os.path.exists(logo_path):
            img_data = Image.open(logo_path)
            self.logo_img = ctk.CTkImage(img_data, img_data, size=(250, 140))
            ctk.CTkLabel(self.center_box, text="", image=self.logo_img).pack(pady=10)

        ctk.CTkLabel(self.center_box, text="FIRELINK", font=("Arial", 32, "bold"), text_color=utils.COLOR_TEXT_LOGO).pack(pady=(0, 30))
        
        self.mode_frame = ctk.CTkFrame(self.center_box, fg_color="transparent")
        self.mode_frame.pack(pady=10)
        self.btn_mode_login = ctk.CTkButton(self.mode_frame, text="Login", width=100, fg_color=utils.COLOR_ACCENT, command=self.show_login)
        self.btn_mode_login.pack(side="left", padx=5)
        self.btn_mode_register = ctk.CTkButton(self.mode_frame, text="Register", width=100, fg_color="transparent", border_width=1, border_color=utils.COLOR_ACCENT, command=self.show_register)
        self.btn_mode_register.pack(side="left", padx=5)

        self.input_frame = ctk.CTkFrame(self.center_box, fg_color="transparent")
        self.input_frame.pack(pady=20)
        self.entry_widget = None 
        self.show_login() 

    def show_login(self):
        self.btn_mode_login.configure(fg_color=utils.COLOR_ACCENT)
        self.btn_mode_register.configure(fg_color="transparent")
        for widget in self.input_frame.winfo_children(): widget.destroy()
        
        users = utils.load_users()
        if not users: users = ["No profiles found"]
        self.entry_widget = ctk.CTkComboBox(self.input_frame, values=users, width=220)
        self.entry_widget.pack(pady=5)
        ctk.CTkButton(self.input_frame, text="Enter", width=220, fg_color=utils.COLOR_ACCENT, hover_color=utils.COLOR_HOVER, command=self.perform_login).pack(pady=15)

    def show_register(self):
        self.btn_mode_login.configure(fg_color="transparent")
        self.btn_mode_register.configure(fg_color=utils.COLOR_ACCENT)
        for widget in self.input_frame.winfo_children(): widget.destroy()
        
        self.entry_widget = ctk.CTkEntry(self.input_frame, placeholder_text="New Username", width=220)
        self.entry_widget.pack(pady=5)
        ctk.CTkButton(self.input_frame, text="Create Profile", width=220, fg_color=utils.COLOR_ACCENT, hover_color=utils.COLOR_HOVER, command=self.perform_register).pack(pady=15)

    def perform_login(self):
        name = self.entry_widget.get()
        if name and name != "No profiles found": self.on_login_success(name)

    def perform_register(self):
        name = self.entry_widget.get()
        if name:
            utils.save_user(name)
            self.on_login_success(name)
            
            # --- HELPER CLASS: ZOOMABLE IMAGE (Put this BEFORE LineupPage) ---
class ZoomableImage(ctk.CTkFrame):
    def __init__(self, master, width, height):
        super().__init__(master, width=width, height=height, fg_color="black")
        
        # Internal State
        self.original_image = None
        self.shown_image = None
        self.scale = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self._drag_data = {"x": 0, "y": 0}

        # The Canvas
        self.canvas = tk.Canvas(self, width=width, height=height, 
                                bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # Bindings
        # Zoom: Windows (MouseWheel), Linux (Button-4/5)
        self.canvas.bind("<MouseWheel>", self.do_zoom) 
        self.canvas.bind("<Button-4>", self.do_zoom)
        self.canvas.bind("<Button-5>", self.do_zoom)
        
        # Pan: Click and Drag
        self.canvas.bind("<ButtonPress-1>", self.start_pan)
        self.canvas.bind("<B1-Motion>", self.do_pan)

    def set_image(self, img_path):
        """Loads a new image and resets zoom"""
        if not os.path.exists(img_path): return

        self.original_image = Image.open(img_path)
        self.scale = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.redraw()

    def redraw(self):
        """Calculates size/position and draws the image"""
        if not self.original_image: return

        # Get current container size (handle startup case where size is 1)
        cw = self.winfo_width() if self.winfo_width() > 1 else self.cget("width")
        ch = self.winfo_height() if self.winfo_height() > 1 else self.cget("height")

        # 1. Calculate new dimensions
        base_w, base_h = self.original_image.size
        new_w = int(base_w * self.scale)
        new_h = int(base_h * self.scale)

        # 2. Resize (LANCZOS for quality)
        resized_pil = self.original_image.resize((new_w, new_h), Image.Resampling.LANCZOS)
        self.shown_image = ctk.CTkImage(light_image=resized_pil, dark_image=resized_pil, size=(new_w, new_h))
        
        # 3. Draw on Canvas
        self.canvas.delete("all")
        
        # Extract tk_image from CTkImage
        tk_img = self.shown_image.create_scaled_photo_image(1.0, "light")
        self.canvas.image = tk_img # Keep reference
        
        # Center of canvas + Pan Offset
        center_x = (cw // 2) + self.pan_x
        center_y = (ch // 2) + self.pan_y
        
        self.canvas.create_image(center_x, center_y, image=tk_img, anchor="center")

    def do_zoom(self, event):
        if event.num == 5 or event.delta < 0:
            self.scale *= 0.9 # Zoom Out
        else:
            self.scale *= 1.1 # Zoom In
            
        # Limits
        if self.scale < 0.1: self.scale = 0.1
        if self.scale > 5.0: self.scale = 5.0
        
        self.redraw()

    def start_pan(self, event):
        self._drag_data = {"x": event.x, "y": event.y}

    def do_pan(self, event):
        dx = event.x - self._drag_data["x"]
        dy = event.y - self._drag_data["y"]
        self.pan_x += dx
        self.pan_y += dy
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y
        self.redraw()

# --- HELPER CLASS: ZOOMABLE IMAGE ---
class ZoomableImage(ctk.CTkFrame):
    def __init__(self, master, width, height):
        super().__init__(master, width=width, height=height, fg_color="black")
        
        # Internal State
        self.original_image = None
        self.shown_image = None
        self.scale = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self._drag_data = {"x": 0, "y": 0}

        # The Canvas
        self.canvas = tk.Canvas(self, width=width, height=height, 
                                bg="black", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # Bindings
        # Zoom: Windows (MouseWheel), Linux (Button-4/5)
        self.canvas.bind("<MouseWheel>", self.do_zoom) 
        self.canvas.bind("<Button-4>", self.do_zoom)
        self.canvas.bind("<Button-5>", self.do_zoom)
        
        # Pan: Click and Drag
        self.canvas.bind("<ButtonPress-1>", self.start_pan)
        self.canvas.bind("<B1-Motion>", self.do_pan)

    def set_image(self, img_path):
        """Loads a new image and resets zoom"""
        if not os.path.exists(img_path): return

        self.original_image = Image.open(img_path)
        self.scale = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.redraw()

    def redraw(self):
        """Calculates size/position and draws the image"""
        if not self.original_image: return

        # Get current container size (handle startup case where size is 1)
        cw = self.winfo_width() if self.winfo_width() > 1 else self.cget("width")
        ch = self.winfo_height() if self.winfo_height() > 1 else self.cget("height")

        # 1. Calculate new dimensions
        base_w, base_h = self.original_image.size
        new_w = int(base_w * self.scale)
        new_h = int(base_h * self.scale)

        # 2. Resize (LANCZOS for quality)
        resized_pil = self.original_image.resize((new_w, new_h), Image.Resampling.LANCZOS)
        self.shown_image = ctk.CTkImage(light_image=resized_pil, dark_image=resized_pil, size=(new_w, new_h))
        
        # 3. Draw on Canvas
        self.canvas.delete("all")
        
        # Extract tk_image from CTkImage
        tk_img = self.shown_image.create_scaled_photo_image(1.0, "light")
        self.canvas.image = tk_img # Keep reference
        
        # Center of canvas + Pan Offset
        center_x = (cw // 2) + self.pan_x
        center_y = (ch // 2) + self.pan_y
        
        self.canvas.create_image(center_x, center_y, image=tk_img, anchor="center")

    def do_zoom(self, event):
        if event.num == 5 or event.delta < 0:
            self.scale *= 0.9 # Zoom Out
        else:
            self.scale *= 1.1 # Zoom In
            
        # Limits
        if self.scale < 0.1: self.scale = 0.1
        if self.scale > 5.0: self.scale = 5.0
        
        self.redraw()

    def start_pan(self, event):
        self._drag_data = {"x": event.x, "y": event.y}

    def do_pan(self, event):
        dx = event.x - self._drag_data["x"]
        dy = event.y - self._drag_data["y"]
        self.pan_x += dx
        self.pan_y += dy
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y
        self.redraw()


# --- LINEUP PAGE (Updated to use ZoomableImage) ---
class LineupPage(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=utils.COLOR_PAGE_BG, corner_radius=0)
        
        # Grid Layout
        self.grid_columnconfigure(0, weight=0) 
        self.grid_columnconfigure(1, weight=0) 
        self.grid_columnconfigure(2, weight=1) 
        self.grid_rowconfigure(0, weight=1)

        # --- COL 1: MAPS SIDEBAR ---
        self.col_maps = ctk.CTkFrame(self, width=140, corner_radius=0, fg_color=utils.COLOR_SIDEBAR)
        self.col_maps.grid(row=0, column=0, sticky="nsew")
        
        ctk.CTkLabel(self.col_maps, text="MAPS", font=("Arial", 16, "bold"), text_color="gray").pack(pady=20)
        
        map_list = ["Mirage", "Inferno", "Dust 2", "Anubis", "Ancient", "Train"]
        for m in map_list:
            ctk.CTkButton(self.col_maps, text=m, fg_color="transparent", anchor="w",
                          command=lambda map_name=m: self.load_map(map_name)).pack(fill="x", padx=10, pady=2)

        # --- COL 2: LINEUPS LIST ---
        self.col_list = ctk.CTkScrollableFrame(self, width=220, corner_radius=0, fg_color="#232323")
        self.col_list.grid(row=0, column=1, sticky="nsew")
        
        self.list_header = ctk.CTkLabel(self.col_list, text="SELECT A MAP", font=("Arial", 14, "bold"), text_color="gray")
        self.list_header.pack(pady=20)

        # --- COL 3: DISPLAY AREA ---
        self.col_display = ctk.CTkFrame(self, fg_color="transparent")
        self.col_display.grid(row=0, column=2, sticky="nsew", padx=30, pady=30)
        
        self.title_lbl = ctk.CTkLabel(self.col_display, text="", font=("Arial", 28, "bold"), text_color="white")
        self.title_lbl.pack(anchor="w", pady=(0, 10))
        
        self.type_badge = ctk.CTkLabel(self.col_display, text="", font=("Arial", 12, "bold"), 
                                       text_color="white", fg_color="gray", corner_radius=6)
        
        # --- CAROUSEL CONTAINER ---
        self.carousel_frame = ctk.CTkFrame(self.col_display, fg_color="transparent")
        self.carousel_frame.pack(fill="both", expand=True, pady=10)

        # Image Box Container
        self.img_container = ctk.CTkFrame(self.carousel_frame, width=800, height=500, fg_color="black")
        self.img_container.pack(pady=10)
        self.img_container.pack_propagate(False) # Keep fixed size
        
        # --- NEW ZOOM WIDGET ---
        self.zoom_widget = ZoomableImage(self.img_container, width=800, height=500)
        self.zoom_widget.pack(fill="both", expand=True)

        # Hint text
        self.hint_lbl = ctk.CTkLabel(self.carousel_frame, text="🖱 Scroll to Zoom • Drag to Pan", 
                                     font=("Arial", 12), text_color="gray")
        self.hint_lbl.pack(pady=(0, 10))

        # CONTROLS (Next/Prev)
        self.controls_frame = ctk.CTkFrame(self.carousel_frame, fg_color="transparent")
        self.controls_frame.pack(pady=5)

        self.btn_prev = ctk.CTkButton(self.controls_frame, text="< Prev", width=80, 
                                      command=self.prev_image, state="disabled")
        self.btn_prev.pack(side="left", padx=10)

        self.lbl_counter = ctk.CTkLabel(self.controls_frame, text="0 / 0", font=("Arial", 14, "bold"))
        self.lbl_counter.pack(side="left", padx=10)

        self.btn_next = ctk.CTkButton(self.controls_frame, text="Next >", width=80, 
                                      command=self.next_image, state="disabled")
        self.btn_next.pack(side="left", padx=10)

        # Description Box
        self.desc_box = ctk.CTkTextbox(self.col_display, height=150, font=("Consolas", 14), 
                                       fg_color="#1a1a1a", text_color="#ddd")
        self.desc_box.pack(fill="x", pady=10)

        # Internal State
        self.current_images = [] # List of filenames
        self.img_index = 0

    def load_map(self, map_name):
        self.list_header.configure(text=f"{map_name.upper()} TACTICS")
        
        for widget in self.col_list.winfo_children():
            if widget != self.list_header:
                widget.destroy()

        lineups = LINEUP_DATA.get(map_name, {})
        if not lineups:
            ctk.CTkLabel(self.col_list, text="No lineups added yet.", text_color="gray").pack(pady=10)
            return

        for name, data in lineups.items():
            btn_color = "transparent"
            if "[SMOKE]" in name: hover = "#5D4037"
            elif "[FLASH]" in name: hover = "#FBC02D"
            elif "[MOLY]" in name: hover = "#D32F2F"
            else: hover = utils.COLOR_HOVER

            ctk.CTkButton(self.col_list, text=name, fg_color=btn_color, hover_color=hover, anchor="w",
                          command=lambda n=name, d=data: self.show_details(n, d)).pack(fill="x", pady=2)

    def show_details(self, name, data):
        self.title_lbl.configure(text=name)
        
        l_type = data.get("type", "General")
        self.type_badge.configure(text=f" {l_type.upper()} ", 
                                  fg_color="#666" if l_type == "Smoke" else "#D32F2F" if l_type == "Molly" else "#FBC02D")
        self.type_badge.pack(anchor="w", pady=(0, 20))

        self.desc_box.delete("0.0", "end")
        self.desc_box.insert("0.0", data.get("desc", "No description."))

        # --- HANDLE IMAGES (List or String) ---
        raw_img = data.get("img")
        
        if isinstance(raw_img, list):
            self.current_images = raw_img
        elif isinstance(raw_img, str):
            self.current_images = [raw_img]
        else:
            self.current_images = []

        self.img_index = 0
        self.update_carousel()

    def update_carousel(self):
        total = len(self.current_images)
        
        # 1. Update Buttons
        if total <= 1:
            self.btn_prev.configure(state="disabled", fg_color="transparent")
            self.btn_next.configure(state="disabled", fg_color="transparent")
            self.lbl_counter.configure(text="")
        else:
            self.btn_prev.configure(state="normal" if self.img_index > 0 else "disabled", 
                                    fg_color=utils.COLOR_ACCENT if self.img_index > 0 else "transparent")
            self.btn_next.configure(state="normal" if self.img_index < total - 1 else "disabled",
                                    fg_color=utils.COLOR_ACCENT if self.img_index < total - 1 else "transparent")
            self.lbl_counter.configure(text=f"{self.img_index + 1} / {total}")

        # 2. Load Image into Zoom Widget
        if total == 0:
            return

        img_name = self.current_images[self.img_index]
        img_path = os.path.join("assets", img_name)
        
        # Pass the file path to the zoom widget
        # It handles all the resizing, centering, and zooming logic internally
        self.zoom_widget.set_image(img_path)

    def next_image(self):
        if self.img_index < len(self.current_images) - 1:
            self.img_index += 1
            self.update_carousel()

    def prev_image(self):
        if self.img_index > 0:
            self.img_index -= 1
            self.update_carousel()
            
# --- APP CONTROLLER ---
class FirelinkApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Firelink")
        self.geometry("1280x800") 
        self.resizable(True, True)

        icon_path = utils.resource_path(os.path.join("img", "fire.ico"))
        if os.path.exists(icon_path): self.iconbitmap(icon_path)

        self.current_frame = None
        self.show_auth()

    def show_auth(self):
        if self.current_frame: self.current_frame.destroy()
        self.current_frame = AuthFrame(self, self.start_dashboard)
        self.current_frame.pack(fill="both", expand=True)

    def start_dashboard(self, username):
        if self.current_frame: self.current_frame.destroy()
        self.current_frame = Dashboard(self, username)
        self.current_frame.pack(fill="both", expand=True)