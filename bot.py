"""
IRC Bot Client

Author: 
Chengyang Zhu 
Zijian Zhou

Date: [2024/9/20]

Description:
This Python script implements an IRC (Internet Relay Chat) bot using sockets and threading. 
The bot connects to an IRC server, joins a specified channel, and interacts with users by responding to specific commands or private messages.


Key Features:
1. the bot connect IRC server using ipv6, and enter the target channel
2. the bot can handle the following command:
- '!hello' command will make the bot say hello to the user
- '!slap' command will simulate an interaction, randomly 'slap' another user in a channel
3. the bot can randomly reply an interesting fact or other replies
4. the bot can relply PING command from server, make sure the connection active
5. the bot can use 'NAME' command to fetch user list in the current channel, making sure it won't 'slap' itself
6. can handle the situation of connection timeout and other exceptions


Usage Instructions:
when running the bot script, use the command line to input Host, port, robot name, and channel to join
python bot.py --host <server address> --port <port> --name <bot name> --channel <channel>
example: python bot.py --host ::1 --port 6667 --name SuperBot --channel hello
NOTICE!: Do not use "#" when entering bot name. eg: use "superbot" instead of "#superbot"
the bot will continue running and listening on target server, you can stop the bot using 'ctrl + c' command

Command-Line Arguments:
1. '--host': address of thge IRC server, defaulted as '::1'(ipv6)
2. `--port`: The port number for the server. Defaults to `6667`.
3. `--name`: The nickname of the bot. Defaults to `SuperBot`.
4. `--channel`: The channel to join. Defaults to `#hello`. If a channel name is passed without the '#' prefix, the bot automatically adds it.


Dependencies:
the bot script uses only the standard python library: 'socket'、'random'、'argparse' and 'threading', please make sure Python3 is installed in your system.
"""

import socket
import random
import argparse
import threading


# Define the bot's command response functionality,
class IRCBot:
    #Bot instantiates datastructures required for network communication

    def __init__(self, host, port, name, channel):
        self.server = host
        self.port = port
        self.name = name
        self.channel = channel
        self.socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        # Keeping the connection to miniircd alive, and managing it efficiently
        # Reasonable timeouts and error handling
        self.socket.settimeout(300)
        self.running = True  # Used to end looping
        self.responses = ["Fun fact: Owls cannot move their eyes!",
                          "Boring fact: You just wasted 2 seconds!",
                          "Random response!"]
        #Bot instantiates datastructures required for network communication
        # Initialize dictionary to store users in each channel
        self.channel_users = {}

    # Connect to the server and join the channel, Bot correctly identify
    # himself to the miniircd server
    def connect(self):
        print(f"Connecting to server {self.server}...")
        self.socket.connect((self.server, self.port, 0, 0))
        self.send_command(f"NICK {self.name}")
        self.send_command(f"USER {self.name} 0 * :{self.name}")
        self.join_channel(self.channel)

    # Send a command to the IRC server
    def send_command(self, command):
        print(f"Sending: {command}")
        self.socket.send((command + "\r\n").encode())

    # Join a channel
    def join_channel(self, channel):
        self.send_command(f"JOIN {channel}")
        self.get_other_users(channel, self.name)  #Get and save user information immediately after joining the channel

    # Handle specific commands
    def process_command(self, user, channel, command):
        if command == "!hello":
            self.send_command(f"PRIVMSG {channel} :Hello {user}!")

        # Handle the !slap command with an optional target
        elif command.startswith("!slap"):
            parts = command.split()
            if len(parts) == 1:  # No specific user provided, randomly slap someone
                other_users = self.get_other_users(channel, user)
                if other_users:
                    target = random.choice(other_users)
                    self.send_command(f"PRIVMSG {channel} :{user} slapped {target} with a trout!")
                else:
                    self.send_command(f"PRIVMSG {channel} :No other users to slap.")
            elif len(parts) == 2:  # A specific user is provided as a target
                target = parts[1]
                other_users = self.get_other_users(channel, user)
                if target in other_users:
                    self.send_command(f"PRIVMSG {channel} :{user} slapped {target} with a trout!")
                else:
                    # If the target is not in the channel, slap the sender
                    self.send_command(f"PRIVMSG {channel} :{user}, {target} is not here, so you slap yourself!")

        # New command: !whois <username>
        elif command.startswith("!whois"):
            parts = command.split()
            if len(parts) == 2:
                target = parts[1]
                self.send_command(f"WHOIS {target}")  # Use IRC WHOIS command to query user info
            else:
                self.send_command(f"PRIVMSG {channel} :Usage: !whois <username>")

        # New command: !list to list all active channels
        elif command == "!list":
            self.send_command("LIST")  # Send the LIST command to the IRC server

    # Handle received messages (updated to handle LIST response)
    def handle_message(self, message):
        print(f"Received message: {message}")
        if message.startswith("PING"):
            self.send_command(f"PONG {message.split()[1]}")  # Respond to server's PING

        # Handle WHOIS response (numeric reply 311 is a common response code for WHOIS)
        elif "311" in message:
            parts = message.split()
            nickname = parts[3]  # This is the nickname being queried
            username = parts[4]
            hostname = parts[5]
            realname = ' '.join(parts[7:])
            response = f"{nickname} is {username}@{hostname} ({realname})"
            self.send_command(f"PRIVMSG {self.channel} :{response}")

        # Handle LIST response (numeric reply 322 is for a channel information)
        elif "322" in message:  # '322' is a numeric reply for LIST response
            parts = message.split()
            channel_name = parts[3]
            user_count = parts[4]
            topic = ' '.join(parts[5:])
            response = f"Channel: {channel_name}, Users: {user_count}, Topic: {topic}"
            self.send_command(f"PRIVMSG {self.channel} :{response}")

        elif "JOIN" in message:
            user = message.split('!')[0][1:]  # Get the username
            channel = message.split()[2]  # Get the channel name
            if channel in self.channel_users:
                self.channel_users[channel].append(user)  # Add the user to the channel's user list
            else:
                self.channel_users[channel] = [user]  # Create a new list if the channel doesn't exist
            print(f"{user} joined {channel}")

        elif "PART" in message:
            user = message.split('!')[0][1:]  # Get the username
            channel = message.split()[2]  # Get the channel name
            if channel in self.channel_users:
                self.channel_users[channel].remove(user)  # Remove the user from the channel's user list
            print(f"{user} left {channel}")

        elif "PRIVMSG" in message:
            user = message.split('!')[0][1:]  # Get the username
            channel = message.split()[2]
            msg_content = message.split(f"PRIVMSG {channel} :")[1]

            if msg_content.startswith("!"):
                self.process_command(user, channel, msg_content.strip())
            else:
                if channel == self.name:  # Private message
                    random_reply = random.choice(self.responses)
                    self.send_command(f"PRIVMSG {user} :{random_reply}")

    def get_other_users(self, channel, exclude_user):
        self.send_command(f"NAMES {channel}")
        response = self.socket.recv(2048).decode("utf-8")
        user_list = []

        # Parse the response to the NAMES command
        for line in response.split("\r\n"):
            if "353" in line:  # '353' is a response code for the NAMES command, indicating the start of the user list
                # Usernames are usually at the end of the line, extract everything after the last ":"
                users = line.split(':')[-1].strip().split()
                for user in users:
                    if user != exclude_user and user != self.name:
                        # Check if the user is the bot itself
                        if user == self.name:
                            print(f"Identified bot: {user}")
                        else:
                            user_list.append(user)

        # Save the user list for the channel
        self.channel_users[channel] = user_list
        return user_list

    # Main loop to continuously receive and process messages
    def run(self):
        while self.running:
            try:
                # Receive data from the socket
                response = self.socket.recv(2048).decode("utf-8")
                if response:
                    for line in response.strip().split("\r\n"):
                        self.handle_message(line)
            except socket.timeout:
                print("Connection timeout.")
                break
            except Exception as e:
                if self.running:  # Only print errors if stopping was not intentional
                    print(f"Error occurred: {e}")
                break
        print("Terminating bot...")

    def stop(self):
        self.running = False
        self.socket.close()


# Use argparse to parse command-line arguments
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IRC bot client")
    parser.add_argument("--host", type=str, default="::1", help="Server address")
    parser.add_argument("--port", type=int, default="6667", help="Server port")
    parser.add_argument("--name", type=str, default="SuperBot", help="Bot's nickname")
    parser.add_argument("--channel", type=str, default="#hello", help="Channel to join")

    args = parser.parse_args()

    # Ensure the channel name starts with '#'
    if not args.channel.startswith('#'):
        args.channel = f'#{args.channel}'

    bot = IRCBot(args.host, args.port, args.name, args.channel)
    bot.connect()

    thread = threading.Thread(target=bot.run)
    thread.start()
    # Send messages
    try:
        while True:
            msg = input()
    except KeyboardInterrupt:
        bot.stop()
        thread.join()
        print("\nExiting client")
