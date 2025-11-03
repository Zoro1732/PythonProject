from socket import *
import os
import base64

#server setup
serverPort = 12000
serverSocket = socket(AF_INET, SOCK_DGRAM)
serverSocket.bind(('', serverPort))
print(f"Server is ready to receive on port {serverPort}")


# Gamer data structure
users = {
    "A" : {"password" : "A", "lives": 2, "avatar": None, "sword": -1, "shield": -1, "slaying_potion": -1, "healing_potion": -1, "active": False},
    "B" : {"password" : "B", "lives": 2, "avatar": None, "sword": -1, "shield": -1, "slaying_potion": -1, "healing_potion": -1, "active": False},
    "C" : {"password" : "C", "lives": 2, "avatar": None, "sword": -1, "shield": -1, "slaying_potion": -1, "healing_potion": -1, "active": False},
    "D" : {"password" : "D", "lives": 2, "avatar": None, "sword": -1, "shield": -1, "slaying_potion": -1, "healing_potion": -1, "active": False}

}

fight_results = [] # store confirmed fight requests

AVATAR_FOLDER = "avatars"
os.makedirs(AVATAR_FOLDER, exist_ok=True)

def send_msg_(msg, addr):
    serverSocket.sendto(msg.encode(), addr)

def list_active_users(exclude_user=None):
    return [u for u, info in users.items() if info["active"] and info["lives"] > 0 and u != exclude_user]

def handle_fight(requester, boss, item, strength):
    att = users[requester]
    defn = users[boss]

    if item == "sword":
        att_attr, def_attr = "sword", "shield"
    else:
        att_attr, def_attr = "slaying_potion", "healing_potion"

    a = strength
    b = defn[def_attr] if defn[def_attr] != -1 else 0

    if a == b:
        att["lives"] -= 1
        defn["lives"] -= 1
        att[att_attr] -= a
        defn[def_attr] += b
        winner = "none"

    elif a > b:
        att["lives"] += 1
        defn["lives"] -= 1
        att[att_attr] -= (a - b)
        defn[def_attr] -= b
        winner = requester
    else:
        att["lives"] -= 1
        defn["lives"] += 1
        att[att_attr] -= a
        defn[def_attr] -= (b - a)
        winner = boss

    fight_results.append({
        "requester": requester,
        "boss": boss,
        "fighting_item": item,
        "fighting_item_strength": a,
        "winner": winner
    })
    return f"FIGHT_RESULT|{winner}"


print("Server is running...")

