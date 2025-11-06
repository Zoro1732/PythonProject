# server.py
# UDP server for simple RPG game assignment

import os
import base64
import json
from socket import socket, AF_INET, SOCK_DGRAM

SERVER_PORT = 12000
BUFFER = 65536
AVATAR_FOLDER = "avatars"
os.makedirs(AVATAR_FOLDER, exist_ok=True)

# initial gamer table (normalized 'password' key to lowercase)
users = {
    "A": {"password": "A", "lives": 2, "avatar": None, "sword": -1, "shield": -1, "slaying_potion": -1, "healing_potion": -1, "active": False},
    "B": {"password": "B", "lives": 2, "avatar": None, "sword": -1, "shield": -1, "slaying_potion": -1, "healing_potion": -1, "active": False},
    "C": {"password": "C", "lives": 2, "avatar": None, "sword": -1, "shield": -1, "slaying_potion": -1, "healing_potion": -1, "active": False},
    "D": {"password": "D", "lives": 2, "avatar": None, "sword": -1, "shield": -1, "slaying_potion": -1, "healing_potion": -1, "active": False},
}

# list of confirmed fight requests (will record fights after processing)
fight_results = []

avatar_buffers = {}

def list_active_usernames(exclude=None):
    return [u for u, info in users.items() if info["active"] and info["lives"] > 0 and u != exclude]

def send(addr, sock, msg):
    try:
        sock.sendto(msg.encode(), addr)
    except Exception as e:
        print("Send error:", e)

def send_json(addr, sock, obj):
    data = json.dumps(obj)
    try:
        sock.sendto(data.encode(), addr)
    except Exception as e:
        print("Send JSON error:", e)

def handle_assign_strengths(username, parts, addr, sock):
    # parts: [sword, shield, slaying, healing]
    try:
        vals = list(map(int, parts))
    except:
        send(addr, sock, "ASSIGN_FAIL|invalid_numbers")
        return
    if any(v < 0 or v > 3 for v in vals):
        send(addr, sock, "ASSIGN_FAIL|values_must_be_0_3")
        return
    if sum(vals) != 10:
        send(addr, sock, "ASSIGN_FAIL|sum_not_10")
        return
    u = users.get(username)
    if not u:
        send(addr, sock, "ASSIGN_FAIL|unknown_user")
        return
    u["sword"], u["shield"], u["slaying_potion"], u["healing_potion"] = vals
    u["active"] = True
    send(addr, sock, "ASSIGN_OK")
    print(f"Assigned strengths for {username}: {vals}")

def handle_upload_avatar(username, b64data, addr, sock):
    try:
        data = base64.b64decode(b64data.encode())
    except Exception:
        send(addr, sock, "UPLOAD_FAIL|bad_base64")
        return
    path = os.path.join(AVATAR_FOLDER, f"{username}.jpg")
    with open(path, "wb") as f:
        f.write(data)
    users[username]["avatar"] = path
    send(addr, sock, "UPLOAD_OK")
    print(f"Avatar saved for {username} -> {path}")

def handle_get_avatar(username, addr, sock):
    path = os.path.join(AVATAR_FOLDER, f"{username}.jpg")
    if not os.path.exists(path):
        send(addr, sock, "AVATAR_NOT_FOUND")
        return
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    chunkSize = 4000
    for i in range(0, len(b64), chunkSize):
        chunk = b64[i:i+chunkSize]
        send(addr,sock, f"AVATAR_CHUNK|{username}|{chunk}")
    send(addr, sock, f"AVATAR_DONE|{username}")
    print(f"Avatar downloaded from \"{username}\"")

def can_use_strength(username, item, strength):
    u = users[username]
    attr = "sword" if item == "sword" else "slaying_potion"
    current = u.get(attr, -1)
    if current == -1:
        current = 0
    return current >= strength

def clamp_strength(v):
    # strengths can go negative in updates, but we keep them >= -1 (unassigned)
    return max(-1, v)

def process_fight(requester, boss, item, strength, addr, sock):
    if requester not in users or boss not in users:
        send(addr, sock, "FIGHT_FAIL|unknown_user")
        return
    if users[requester]["lives"] <= 0:
        send(addr, sock, "FIGHT_FAIL|requester_dead")
        return
    if users[boss]["lives"] <= 0:
        send(addr, sock, "FIGHT_FAIL|boss_dead")
        return
    # check attacker has enough strength on server-side
    att_attr = "sword" if item == "sword" else "slaying_potion"
    def_attr = "shield" if item == "sword" else "healing_potion"

    try:
        a = int(strength)
    except:
        send(addr, sock, "FIGHT_FAIL|bad_strength")
        return

    # treat unassigned (-1) as 0 for comparison but fights should be allowed only if requester has sufficient resource
    if users[requester][att_attr] == -1:
        send(addr, sock, "FIGHT_FAIL|attacker_unassigned")
        return
    if users[requester][att_attr] < a:
        send(addr, sock, "FIGHT_FAIL|not_enough_strength")
        return

    b = users[boss][def_attr] if users[boss][def_attr] != -1 else 0

    # apply rules per assignment:
    # 1) if equal: both lose 1 life; attacker loses a sword strength; defender loses b shield strength
    # 2) attacker > defender: attacker gains 1 life, defender loses 1 life
    #    attacker loses (a - b) strengths; defender loses b strengths
    # 3) attacker < defender: attacker loses 1 life, defender gains 1 life
    #    attacker loses a strengths; defender loses (b - a) strengths
    if a == b:
        users[requester]["lives"] = max(0, users[requester]["lives"] - 1)
        users[boss]["lives"] = max(0, users[boss]["lives"] - 1)
        users[requester][att_attr] = clamp_strength(users[requester][att_attr] - a)
        users[boss][def_attr] = clamp_strength(users[boss][def_attr] - b)
        winner = "none"
    elif a > b:
        users[requester]["lives"] += 1
        users[boss]["lives"] = max(0, users[boss]["lives"] - 1)
        users[requester][att_attr] = clamp_strength(users[requester][att_attr] - (a - b))
        users[boss][def_attr] = clamp_strength(users[boss][def_attr] - b)
        winner = requester
    else:  # a < b
        users[requester]["lives"] = max(0, users[requester]["lives"] - 1)
        users[boss]["lives"] += 1
        users[requester][att_attr] = clamp_strength(users[requester][att_attr] - a)
        users[boss][def_attr] = clamp_strength(users[boss][def_attr] - (b - a))
        winner = boss

    # deactivate those with lives == 0 or unassigned sword (-1)
    for uname in (requester, boss):
        u = users[uname]
        if u["lives"] <= 0 or u["sword"] == -1:
            u["active"] = False
    # record fight
    fight = {
        "requester": requester,
        "boss": boss,
        "fighting_item": item,
        "fighting_item_strength": a,
        "winner": winner
    }
    fight_results.append(fight)
    #send(addr, sock, "FIGHT_RESULT|" + json.dumps(fight))
    send(addr, sock, "FIGHT_RESULT|" + f"{requester} fought {boss}...")
    print("Fight processed:", fight)

def handle_get_active_info(addr, sock):
    # return full info of active gamers
    active = {u: info for u, info in users.items() if info["active"] and info["lives"] > 0}
    # remove avatar path (replace with True/False) to avoid sending file paths
    for k in list(active.keys()):
        active[k] = active[k].copy()
        active[k]["has_avatar"] = bool(active[k].get("avatar"))
        active[k].pop("avatar", None)
    send_json(addr, sock, {"active_info": active})

def handle_get_fights(addr, sock):
    send_json(addr, sock, {"fights": fight_results})

def handle_get_state(username, addr, sock):
    u = users.get(username)
    if not u:
        send(addr, sock, "STATE_FAIL|unknown_user")
        return
    # copy and mask avatar path
    state = u.copy()
    state["has_avatar"] = bool(state.get("avatar"))
    state.pop("avatar", None)
    # if unassigned (-1) display "unassigned" for client convenience
    for key in ("sword", "shield", "slaying_potion", "healing_potion"):
        if state[key] == -1:
            state[key] = "unassigned"
    send_json(addr, sock, {f"state": state})

def main():
    sock = socket(AF_INET, SOCK_DGRAM)
    sock.bind(('', SERVER_PORT))
    print(f"Server is ready on UDP port {SERVER_PORT}")

    while True:
        try:
            data, addr = sock.recvfrom(BUFFER)
            text = data.decode(errors='ignore').strip()
            if not text:
                continue
            parts = text.split("|")
            cmd = parts[0]
            print(f"Received from {addr}: {text}")

            if cmd == "LOGIN":
                # LOGIN|username|password
                if len(parts) < 3:
                    send(addr, sock, "LOGIN_FAIL|missing")
                    continue

                username, password = parts[1], parts[2]
                user = users.get(username)
                if user is None:
                    send(addr, sock, "LOGIN_FAIL|bad_credentials")
                    print(f"\"{username}\" is not a registered user. Please try logging in again.")
                    continue

                if user["lives"] <= 0:
                    # player has no lives -> game over
                    send(addr, sock, "LOGIN_FAIL|game_over")
                    print(f"\"{username}\" has 0 lives! This account can no longer be logged into.")
                    continue

                if user["password"] == password:
                    send(addr, sock, "LOGIN_OK")
                    print(f"User {username} is now authenticated.")
                    # Also send the state as required by assignment (server-side)
                    handle_get_state(username, addr, sock)
                else:
                    send(addr, sock, "LOGIN_FAIL|bad_credentials")
                    print(f"Could not log into account \"{username}\". Please try logging in again.")

            elif cmd == "GET_STATE":
                # GET_STATE|username
                if len(parts) < 2:
                    send(addr, sock, "STATE_FAIL|missing_username")
                    continue
                handle_get_state(parts[1], addr, sock)

            elif cmd == "UPLOAD_AVATAR":
                # UPLOAD_AVATAR|username|base64data
                if len(parts) < 3:
                    send(addr, sock, "UPLOAD_FAIL|missing")
                    continue
                handle_upload_avatar(parts[1], parts[2], addr, sock)

            elif cmd == "UPLOAD_AVATAR_CHUNK":
                if len(parts) < 4:
                    send(addr, sock, "CHUNK_FAIL|missing")
                    continue
                username = parts[1]
                try:
                    offset = int(parts[2])
                except:
                    send(addr, sock, "CHUNK_FAIL|bad_offset")
                    continue
                chunk = parts[3]

                if username not in avatar_buffers:
                    avatar_buffers[username] = {}
                avatar_buffers[username][offset] = chunk

                send(addr, sock, "CHUNK_OK")

            elif cmd == "UPLOAD_AVATAR_DONE":
                if len(parts) < 2:
                    send(addr, sock, "UPLOAD_FAIL|missing_username")
                    continue
                username = parts[1]
                chunks = avatar_buffers.pop(username, {})
                if not chunks:
                    send(addr, sock, "UPLOAD_FAIL|no_chunks")
                    continue

                ordered_data = "".join(chunks[k] for k in sorted(chunks))
                handle_upload_avatar(username, ordered_data, addr, sock)

            elif cmd == "GET_AVATAR":
                # GET_AVATAR|target_username
                if len(parts) < 2:
                    send(addr, sock, "AVATAR_NOT_FOUND")
                    continue
                handle_get_avatar(parts[1], addr, sock)

            elif cmd == "ASSIGN":
                # ASSIGN|username|sword|shield|slaying|healing
                if len(parts) < 6:
                    send(addr, sock, "ASSIGN_FAIL|missing")
                    continue
                handle_assign_strengths(parts[1], parts[2:6], addr, sock)

            elif cmd == "LIST_ACTIVE":
                # LIST_ACTIVE|username (username optional, to exclude self)
                exclude = parts[1] if len(parts) > 1 else None
                active = list_active_usernames(exclude)
                send_json(addr, sock, {"active_usernames": active})

            elif cmd == "FIGHT":
                # FIGHT|requester|boss|item|strength
                if len(parts) < 5:
                    send(addr, sock, "FIGHT_FAIL|missing")
                    continue
                process_fight(parts[1], parts[2], parts[3], parts[4], addr, sock)

            elif cmd == "GET_FIGHTS":
                handle_get_fights(addr, sock)

            elif cmd == "GET_ACTIVE_INFO":
                handle_get_active_info(addr, sock)

            elif cmd == "QUIT":
                # QUIT|username
                uname = parts[1] if len(parts) > 1 else None
                if uname and uname in users:
                    users[uname]["active"] = False
                print(f"User {uname} disconnected (QUIT).")
                send(addr, sock, "QUIT_OK")

            else:
                send(addr, sock, "ERR|unknown_command")

        except Exception as e:
            print("Server error:", e)

if __name__ == "__main__":
    main()
