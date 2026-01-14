import customtkinter as ctk
import ctypes
import gui # Import our new GUI file

# --- WINDOWS AWAKE MODE ---
try: ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)
except: pass

ctk.set_appearance_mode("Dark")

if __name__ == "__main__":
    app = gui.FirelinkApp()
    app.mainloop()