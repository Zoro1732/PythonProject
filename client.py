# client_gui.py
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog
import base64
import json
import os
import threading
from socket import socket, AF_INET, SOCK_DGRAM

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 12000
BUFFER = 65536
AVATAR_DOWNLOADS = "downloaded_avatars"
os.makedirs(AVATAR_DOWNLOADS, exist_ok=True)

sock = socket(AF_INET, SOCK_DGRAM)
server_addr = (SERVER_HOST, SERVER_PORT)

def send_and_recv(msg):
    # send a UDP message and wait for single reply
    try:
        sock.sendto(msg.encode(), server_addr)
        data, _ = sock.recvfrom(BUFFER)
        text = data.decode(errors='ignore')
        try:
            return json.loads(text)
        except:
            return text
    except Exception as e:
        return f"ERROR_COMM|{e}"

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
            messagebox.showwarning("Input Error", "Please enter both your username and password.")
            return

        res = send_and_recv(f"LOGIN|{username}|{password}")
        # server may respond with "LOGIN_OK" and also send a JSON state (server may send state separately)
        # we handle the expected responses:
        print(res)
        if isinstance(res, str):
            if res.startswith("LOGIN_OK"):
                # login success: set username, then explicitly request GET_STATE to ensure we have a state
                self.app.username = username
                messagebox.showinfo("Log-in SUCCESS", f"Logging into account: \"{username}\"")
                # move to main menu
                self.app.show_frame("MainMenuFrame")
                main_frame = self.app.frames["MainMenuFrame"]
                # fetch and display state automatically
                state_res = main_frame.get_state(auto=True)
                # if state indicates sword unassigned, prompt assignment
                if isinstance(state_res, dict) and "state" in state_res:
                    s = state_res["state"]
                    if s.get("sword") == "unassigned":
                        # prompt to assign strengths now
                        if messagebox.askyesno(f"Assigning Strengths for {username}", "You are given 10 stat points. Do you want to assign them to your attributes?"):
                            main_frame.assign_strengths(auto=True)

                        else:
                            # optionally ask about upload avatar
                            if messagebox.askyesno("Upload Avatar", "Do you want to upload an avatar now?"):
                                main_frame.upload_avatar()
                    else:
                        # sword already assigned: ask about avatar upload
                        if messagebox.askyesno("Upload Avatar", "Do you want to upload an avatar now?"):
                            main_frame.upload_avatar()
                return
            elif res.startswith("LOGIN_FAIL|game_over"):
                messagebox.showerror("Game Over", "GAME OVER! Your account has 0 lives!. You cannot log in anymore.")
                return
            elif res.startswith("LOGIN_FAIL"):
                # login failed: show retry/quit menu
                retry = messagebox.askretrycancel("Login Failed", f"Login attempt failed. \nRetry?")
                if not retry:
                    self.app.destroy()
                return
            else:
                # unknown string response
                messagebox.showerror("Login Error", f"Unknown login information detected")
                return
        else:
            # if server sent JSON instead of string (unlikely), handle it
            messagebox.showinfo("Login", f"Unusual response detected.")

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
        ttk.Button(btn_frame, text="FIGHT", command=self.fight).grid(row=1, column=1, padx=5, pady=5)
        ttk.Button(btn_frame, text="Get Active Info", command=self.get_active_info).grid(row=1, column=2, padx=5, pady=5)
        ttk.Button(btn_frame, text="Upload Avatar", command=self.upload_avatar).grid(row=2, column=0, padx=5, pady=5)
        ttk.Button(btn_frame, text="Download Avatar", command=self.download_avatar).grid(row=2, column=1, padx=5, pady=5)
        ttk.Button(btn_frame, text="Quit", command=self.quit_game).grid(row=2, column=2, padx=5, pady=5)

        # Output area
        self.output = tk.Text(self, wrap="word", height=15, width=80)
        self.output.pack(pady=10)

    # ------------- Command Functions ------------- #
    def get_state(self, auto=False):
        username = self.app.username
        if not username:
            messagebox.showwarning("Not logged in", "You must log in first.")
            return
        res = send_and_recv(f"GET_STATE|{username}")
        # display
        if not auto:
            self.app.send_and_display(f"Stats for: \"{username}\"", self.output)
        else:
            # auto: still display
            if isinstance(res, (dict, list)):
                self.output.insert(tk.END, f"\nGET_STATE|{username}\n{json.dumps(res, indent=2)}\n")
            else:
                self.output.insert(tk.END, f"\nGET_STATE|{username}\n{res}\n")
            self.output.see(tk.END)
        return res

    def assign_strengths(self, auto=False):
        username = self.app.username
        if not username:
            messagebox.showwarning("Not logged in", "You must log in first.")
            return

        # If auto, present sequential small dialog inputs; otherwise show the same Toplevel UI
        if auto:
            # sequentially ask for four ints
            vals = []
            props = ["sword", "shield", "slaying_potion", "healing_potion"]
            for p in props:
                v = simpledialog.askstring("Assigning Strengths", f"Enter your stats for {p}:")
                if v is None:
                    messagebox.showinfo("Assign Strengths", "Assignment cancelled.")
                    return
                vals.append(v.strip())
            if len(vals) != 4:
                messagebox.showerror("Error", "You must enter 4 values.")
                return
            msg = f"ASSIGN|{username}|{'|'.join(vals)}"
            self.app.send_and_display(msg, self.output)
            return

        top = tk.Toplevel(self)
        top.title("Assign Strengths")
        tk.Label(top, text="Enter 4 integers [0..3] totaling to 10 for: sword, shield, slaying, healing):").pack(pady=5)
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
        if not username:
            messagebox.showwarning("Not logged in", "You must log in first.")
            return
        self.app.send_and_display(f"LIST_ACTIVE|{username}", self.output)

    def get_fights(self):
        self.app.send_and_display("GET_FIGHTS", self.output)

    def fight(self):
        username = self.app.username
        if not username:
            messagebox.showwarning("Not logged in", "You must log in first.")
            return
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
            # after a fight, optionally ask to send another fight
            if messagebox.askyesno("Fight again?", "Do you want to send another fight request?"):
                self.fight()
        tk.Button(top, text="Fight!", command=send_fight).pack(pady=10)

    def get_active_info(self):
        self.app.send_and_display("GET_ACTIVE_INFO", self.output)

    def upload_avatar(self):
        username = self.app.username
        if not username:
            messagebox.showwarning("Not logged in", "You must log in first.")
            return
        path = filedialog.askopenfilename(title="Select JPG", filetypes=[("JPEG files", "*.jpg;*.jpeg")])
        if not path:
            return

        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()

        chunk_size = 4000
        total_length = len(b64)
        for i in range(0, len(b64), chunk_size):
            chunk = b64[i:i + chunk_size]
            msg = f"UPLOAD_AVATAR_CHUNK|{username}|{i}|{chunk}"
            # silent send of chunks
            send_and_recv(msg)

        send_and_recv(f"UPLOAD_AVATAR_DONE|{username}")
        self.output.insert(tk.END, f"\nAvatar has been uploaded!\n")
        self.output.see(tk.END)

    def download_avatar(self):
        uname = simpledialog.askstring("Download Avatar", "Enter the username you want to download from:")
        if not uname:
            return
        sock.sendto(f"GET_AVATAR|{uname}".encode(), server_addr)
        avatar_data = ""
        while True:
            resp, _ = sock.recvfrom(BUFFER)
            msg = resp.decode(errors='ignore')
            if msg.startswith("AVATAR_CHUNK"):
                parts = msg.split("|",2)
                avatar_data += parts[2]
            elif msg.startswith("AVATAR_DONE"):
                break
            elif msg.startswith("AVATAR_NOT_FOUND"):
                messagebox.showerror("DOWNLOAD ERROR", f"Avatar for {uname} could not be found!")
                return
        path = os.path.join(AVATAR_DOWNLOADS, f"{uname}.jpg")
        with open(path,"wb") as f:
            f.write(base64.b64decode(avatar_data))
        messagebox.showinfo("SUCCESS", f"Avatar has been downloaded!\n")
        self.output.insert(tk.END, f"\nDownloaded avatar for {uname}.")
        self.output.see(tk.END)

    def quit_game(self):
        username = self.app.username
        res = send_and_recv(f"QUIT|{username}" if username else "QUIT|")
        messagebox.showinfo("Quit", f"Logging off of account: \"{username}\"")
        self.app.destroy()


if __name__ == "__main__":
    app = RPGClientApp()
    app.mainloop()