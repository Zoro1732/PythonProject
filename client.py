# client_gui.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import base64
import json
import os
from socket import socket, AF_INET, SOCK_DGRAM

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 12000
BUFFER = 65536
AVATAR_DOWNLOADS = "downloaded_avatars"
os.makedirs(AVATAR_DOWNLOADS, exist_ok=True)

sock = socket(AF_INET, SOCK_DGRAM)
server_addr = (SERVER_HOST, SERVER_PORT)

def send_and_recv(msg):
    sock.sendto(msg.encode(), server_addr)
    data, _ = sock.recvfrom(BUFFER)
    text = data.decode(errors='ignore')
    try:
        return json.loads(text)
    except:
        return text

# ---------------- UI Class ---------------- #
class RPGClientApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Simple RPG Client")
        self.geometry("700x500")
        self.username = None

        self.container = ttk.Frame(self)
        self.container.pack(fill="both", expand=True)

        self.frames = {}
        for F in (LoginFrame, MainMenuFrame):
            frame = F(parent=self.container, app=self)
            self.frames[F.__name__] = frame
            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame("LoginFrame")

    def show_frame(self, name):
        frame = self.frames[name]
        frame.tkraise()

    def send_and_display(self, msg, output_widget):
        res = send_and_recv(msg)
        if isinstance(res, (dict, list)):
            formatted = json.dumps(res, indent=2)
        else:
            formatted = str(res)
        output_widget.insert(tk.END, f"\n> {msg}\n{formatted}\n")
        output_widget.see(tk.END)
        return res


# ---------------- Login Frame ---------------- #
class LoginFrame(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        ttk.Label(self, text="Simple RPG Login", font=("Arial", 18, "bold")).pack(pady=20)
        self.user_entry = ttk.Entry(self, width=30)
        self.pass_entry = ttk.Entry(self, width=30, show="*")

        ttk.Label(self, text="Username:").pack(pady=(10,0))
        self.user_entry.pack()
        ttk.Label(self, text="Password:").pack(pady=(10,0))
        self.pass_entry.pack()

        ttk.Button(self, text="Login", command=self.login).pack(pady=20)

    def login(self):
        username = self.user_entry.get().strip()
        password = self.pass_entry.get().strip()
        if not username or not password:
            messagebox.showwarning("Input Error", "Please enter both username and password.")
            return
        res = send_and_recv(f"LOGIN|{username}|{password}")
        if isinstance(res, str) and res.startswith("LOGIN_OK"):
            self.app.username = username
            messagebox.showinfo("Success", f"Welcome, {username}!")
            self.app.show_frame("MainMenuFrame")
        else:
            messagebox.showerror("Login Failed", f"Server response: {res}")


# ---------------- Main Menu Frame ---------------- #
class MainMenuFrame(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app

        title = ttk.Label(self, text="RPG Game Menu", font=("Arial", 16, "bold"))
        title.pack(pady=10)

        # Buttons area
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Get State", command=self.get_state).grid(row=0, column=0, padx=5, pady=5)
        ttk.Button(btn_frame, text="Assign Strengths", command=self.assign_strengths).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(btn_frame, text="List Active Users", command=self.list_active).grid(row=0, column=2, padx=5, pady=5)
        ttk.Button(btn_frame, text="Get Fights", command=self.get_fights).grid(row=1, column=0, padx=5, pady=5)
        ttk.Button(btn_frame, text="Fight", command=self.fight).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(btn_frame, text="Get Active Info", command=self.get_active_info).grid(row=1, column=2, padx=5, pady=5)
        ttk.Button(btn_frame, text="Upload Avatar", command=self.upload_avatar).grid(row=2, column=0, padx=5, pady=5)
        ttk.Button(btn_frame, text="Download Avatar", command=self.download_avatar).grid(row=2, column=1, padx=5, pady=5)
        ttk.Button(btn_frame, text="Quit", command=self.quit_game).grid(row=2, column=2, padx=5, pady=5)

        # Output area
        self.output = tk.Text(self, wrap="word", height=15, width=80)
        self.output.pack(pady=10)

    # ------------- Command Functions ------------- #
    def get_state(self):
        username = self.app.username
        self.app.send_and_display(f"GET_STATE|{username}", self.output)

    def assign_strengths(self):
        username = self.app.username
        top = tk.Toplevel(self)
        top.title("Assign Strengths")
        tk.Label(top, text="Enter 4 integers [0..3] summing to 10 (sword, shield, slaying, healing):").pack(pady=5)
        entry = tk.Entry(top, width=30)
        entry.pack(pady=5)
        def send_assign():
            vals = entry.get().split()
            if len(vals) != 4:
                messagebox.showerror("Error", "You must enter 4 values.")
                return
            msg = f"ASSIGN|{username}|{'|'.join(vals)}"
            self.app.send_and_display(msg, self.output)
            top.destroy()
        tk.Button(top, text="Send", command=send_assign).pack(pady=10)

    def list_active(self):
        username = self.app.username
        self.app.send_and_display(f"LIST_ACTIVE|{username}", self.output)

    def get_fights(self):
        self.app.send_and_display("GET_FIGHTS", self.output)

    def fight(self):
        username = self.app.username
        top = tk.Toplevel(self)
        top.title("Fight Menu")
        tk.Label(top, text="Opponent username:").pack()
        user_entry = tk.Entry(top)
        user_entry.pack()
        tk.Label(top, text="Item (sword/slaying_potion):").pack()
        item_entry = tk.Entry(top)
        item_entry.pack()
        tk.Label(top, text="Strength (0-3):").pack()
        strength_entry = tk.Entry(top)
        strength_entry.pack()

        def send_fight():
            boss = user_entry.get().strip()
            item = item_entry.get().strip()
            s = strength_entry.get().strip()
            msg = f"FIGHT|{username}|{boss}|{item}|{s}"
            self.app.send_and_display(msg, self.output)
            top.destroy()
        tk.Button(top, text="Fight!", command=send_fight).pack(pady=10)

    def get_active_info(self):
        self.app.send_and_display("GET_ACTIVE_INFO", self.output)

    def upload_avatar(self):
        username = self.app.username
        path = filedialog.askopenfilename(title="Select JPG", filetypes=[("JPEG files", "*.jpg;*.jpeg")])
        if not path:
            return
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        msg = f"UPLOAD_AVATAR|{username}|{b64}"
        self.app.send_and_display(msg, self.output)

    def download_avatar(self):
        target = tk.simpledialog.askstring("Download Avatar", "Enter username to download:")
        if not target:
            return
        res = send_and_recv(f"GET_AVATAR|{target}")
        if isinstance(res, str) and res.startswith("AVATAR|"):
            _, uname, b64 = res.split("|", 2)
            data = base64.b64decode(b64)
            out = os.path.join(AVATAR_DOWNLOADS, f"{uname}.jpg")
            with open(out, "wb") as f:
                f.write(data)
            messagebox.showinfo("Success", f"Saved avatar to {out}")
        else:
            messagebox.showerror("Error", f"Avatar not found or error: {res}")

    def quit_game(self):
        username = self.app.username
        res = send_and_recv(f"QUIT|{username}")
        messagebox.showinfo("Quit", str(res))
        self.app.destroy()


if __name__ == "__main__":
    app = RPGClientApp()
    app.mainloop()
