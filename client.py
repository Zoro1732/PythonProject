from socket import *
# setting the server name & port (assumed to be pre-defined)
serverName = 'localhost'
serverPort = 12000
# creating the clientSocket (assumed to be "opening" it)
clientSocket = socket(AF_INET, SOCK_DGRAM)

# while-loop that will ask the user to enter their login info, breaking out when they successfully do so
while True:
    # making sure to validate the user by asking for their username & password
    username = input("\nEnter your username: ")
    password = input("\nPassword: ")

    # sending the username & password to the server to validate
    clientSocket.sendto(username.encode(), (serverName, serverPort))
    clientSocket.sendto(password.encode(), (serverName, serverPort))

    # -- GO INTO server.py TO TRACE -- #

    # receiving, decrypting, & displaying the serverLoginResponse
    loginValidation, serverAddress = clientSocket.recvfrom(2048)
    serverLoginResponse = loginValidation.decode()
    print(serverLoginResponse)

    # "if the server responds with a 'SUCCESS' then break out of the loop to continue onward"
    if "SUCCESS" in serverLoginResponse:
        break


# asking the user to enter their stat values, where all 10 points must be used
# printing user instructions
print("You are gamer. You have 10 stat points to put into the following attributes:\n")
print("An attribute can only have a max value of 3 and all 10 stat points must be used in order to continue.\n")

# "get" messages for each attribute
getStrengthM = input("\nStrength: ")
getShieldM = input("\nShield: ")
getSlayingM = input("\nSlaying Potion: ")
getHealingM = input("\nHealing Potion: ")

# trying to convert the above stats to integers, making exceptions for any non-integer values
try:
    strengthValue = int(getStrengthM)
    shieldValue = int(getShieldM)
    slayingPotionValue = int(getSlayingM)
    healingPotionValue = int(getHealingM)

except ValueError:
    # printing errors & closing the program (might need to change)
    print("ERROR: Non-integer values detected.")
    clientSocket.close()
    exit()


# sending the messages into the server to assign them...?
clientSocket.sendto(getStrengthM.encode(),(serverName, serverPort))
clientSocket.sendto(getShieldM.encode(),(serverName, serverPort))
clientSocket.sendto(getSlayingM.encode(),(serverName, serverPort))
clientSocket.sendto(getHealingM.encode(),(serverName, serverPort))

modifiedMessage, serverAddress = clientSocket.recvfrom(2048)
print (modifiedMessage.decode())
clientSocket.close()