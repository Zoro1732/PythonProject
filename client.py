# client.py
# Simple UDP client to interact with the game server
import base64
import json
import os
from socket import socket, AF_INET, SOCK_DGRAM

SERVER_HOST = "127.0.0.1"   # change to server IP if remote
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
    # try JSON decode
    try:
        return json.loads(text)
    except:
        return text

def login():
    username = input("username: ").strip()
    password = input("password: ").strip()
    res = send_and_recv(f"LOGIN|{username}|{password}")
    if isinstance(res, str) and res.startswith("LOGIN_OK"):
        print("Login successful")
        return username
    else:
        print("Login failed:", res)
        return None

def get_state(username):
    res = send_and_recv(f"GET_STATE|{username}")
    print("State response:", res)

def upload_avatar(username):
    path = input("path to jpg to upload: ").strip()
    if not os.path.exists(path):
        print("file not found")
        return
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    res = send_and_recv(f"UPLOAD_AVATAR|{username}|{b64}")
    print("Upload result:", res)

def download_avatar():
    target = input("download avatar of username: ").strip()
    res = send_and_recv(f"GET_AVATAR|{target}")
    if isinstance(res, str) and res.startswith("AVATAR|"):
        _, uname, b64 = res.split("|", 2)
        data = base64.b64decode(b64)
        out = os.path.join(AVATAR_DOWNLOADS, f"{uname}.jpg")
        with open(out, "wb") as f:
            f.write(data)
        print("Saved avatar to", out)
    else:
        print("Avatar not found or error:", res)

def assign_strengths(username):
    print("Enter 4 integers in [0..3] for sword, shield, slaying_potion, healing_potion summing to 10.")
    s = input("sword shield slaying healing (space separated): ").strip().split()
    if len(s) != 4:
        print("need 4 numbers")
        return
    res = send_and_recv(f"ASSIGN|{username}|{s[0]}|{s[1]}|{s[2]}|{s[3]}")
    print("Assign result:", res)

def list_active(username):
    res = send_and_recv(f"LIST_ACTIVE|{username}")
    print("Active users:", res)

def get_fights():
    res = send_and_recv("GET_FIGHTS")
    print("Confirmed fights (structured):")
    print(json.dumps(res, indent=2))

def fight(username):
    boss = input("who do you want to fight (username): ").strip()
    item = input("which item (sword/slaying_potion) type exactly 'sword' or 'slaying_potion': ").strip()
    strength = input("strength to use [0..3]: ").strip()
    # local check optional: ensure attacker has enough strength? server also checks
    res = send_and_recv(f"FIGHT|{username}|{boss}|{item}|{strength}")
    print("Fight response:", res)

def get_active_info():
    res = send_and_recv("GET_ACTIVE_INFO")
    print("Active gamers full info:")
    print(json.dumps(res, indent=2))

def main():
    print("Welcome to simple RPG client")
    username = None
    while not username:
        username = login()
    # get initial state
    get_state(username)

    while True:
        print("\ncommands: upload_avatar, download_avatar, assign, list_active, get_fights, fight, get_active_info, state, quit")
        cmd = input("> ").strip().lower()
        if cmd == "upload_avatar":
            upload_avatar(username)
        elif cmd == "download_avatar":
            download_avatar()
        elif cmd == "assign":
            assign_strengths(username)
        elif cmd == "list_active":
            list_active(username)
        elif cmd == "get_fights":
            get_fights()
        elif cmd == "fight":
            fight(username)
        elif cmd == "get_active_info":
            get_active_info()
        elif cmd == "state":
            get_state(username)
        elif cmd == "quit":
            res = send_and_recv(f"QUIT|{username}")
            print("Quit:", res)
            break
        else:
            print("unknown command")

if __name__ == "__main__":
    main()
