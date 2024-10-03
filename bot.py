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
1. The bot connects to an IRC server using IPv6 and enters the target channel.
2. The bot can handle the following commands:
   - '!hello' command will make the bot say hello to the user.
   - '!slap' command will simulate an interaction, randomly 'slap' another user in a channel.
3. The bot can randomly reply with an interesting fact or other replies.
4. The bot can reply to PING commands from the server to ensure the connection stays active.
5. The bot can use the 'NAMES' command to fetch the user list in the current channel, ensuring it won't 'slap' itself.
6. It can handle situations like connection timeouts and other exceptions.

Usage Instructions:
When running the bot script, use the command line to input the host, port, bot name, and channel to join:
python bot.py --host <server address> --port <port> --name <bot name> --channel <channel>
Example: python bot.py --host ::1 --port 6667 --name SuperBot --channel hello
NOTICE!: Do not use "#" when entering the bot name. eg: use "superbot" instead of "#superbot".
The bot will continue running and listening on the target server, and you can stop the bot using the 'ctrl + c' command.

Command-Line Arguments:
1. '--host': Address of the IRC server, defaulted to '::1' (IPv6).
2. '--port': The port number for the server, defaulting to 6667.
3. '--name': The nickname of the bot, defaulted to 'SuperBot'.
4. '--channel': The channel to join, defaulted to '#hello'. If a channel name is passed without the '#' prefix, the bot automatically adds it.

Dependencies:
The bot script uses only the standard Python library: 'socket', 'random', 'argparse', and 'threading'. Please ensure Python3 is installed on your system.
"""

import socket
import random
import argparse
import threading
import os
import time


# Define the bot's command response functionality
class IRCBot:
    # Bot instantiates the data structures required for network communication

    def __init__(self, host, port, name, channel):
        self.server = host
        self.port = port
        self.name = name
        self.channel = channel
        self.socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)  # Use IPv6 socket
        # Set a reasonable timeout and handle errors
        self.socket.settimeout(300)
        self.running = True  # Used to control the main loop
        self.responses = self.load_facts()
        # Initialize a dictionary to store users in each channel
        self.channel_users = {}
        self.server_info={}


    def load_facts(self):
        facts_file = "facts.txt"
        facts = []
        if os.path.exists(facts_file):
            with open(facts_file, "r", encoding="utf-8") as f:
                facts = f.read().splitlines()  #
        else:
            print(f"{facts_file} File not found.")
        return facts


    # Send a command to the IRC server
    def send_message(self,command):
        if self.socket:
            print(f"Sending: {command}")
            self.socket.send((command + "\r\n").encode())  # Send the command to the server
        else:
            print(f"Cannot send: {command} as the socket has closed.")

    # Run a thread to send the command
    def send_command(self, command):
        send_thread = threading.Thread(target=self.send_message, args=(command,))
        send_thread.start()

    # Join a channel and fetch the user list
    def join_channel(self, channel):
        self.send_command(f"JOIN {channel}")
        self.send_command(f"NAMES {channel}")  # Send NAMES command to get user list


    # Handle incoming messages from the server
    def handle_message(self, message):
        print(f"Received message: {message}")
        if message.startswith("PING"):  # Handle server PING
            self.send_command(f"PONG {message.split()[1]}")  # Respond to the PING to keep the connection alive
            return

        components = message.split()
        prefix = components[0]
        command = components[1]
        params = components[2:-1]
        content = components[-1]

        user = prefix.split('!')[0][1:]  # Extract the username

        if user == self.name:  # Ignore messages from the bot itself
            return

        if command == "001":  # Welcome message
            self.server_info["welcome"] = message.split(":", 2)[-1]
            print(f"Welcome: {self.server_info['welcome']}")
        elif command == "002":  # Host information
            self.server_info["host"] = message.split(":", 2)[-1]
            print(f"Host: {self.server_info['host']}")
        elif command == "003":  # Server creation information
            self.server_info["creation"] = message.split(":", 2)[-1]
            print(f"Creation: {self.server_info['creation']}")
        elif command == "004":  # Server and version details
            self.server_info["version"] = params[1:]  # Server name and version
            print(f"Version: {self.server_info['version']}")
        elif command == "251":  # Server user statistics
            self.server_info["user_stats"] = message.split(":", 2)[-1]
            print(f"User stats: {self.server_info['user_stats']}")
        elif command == "422":  # MOTD missing
            self.server_info["motd"] = "MOTD is missing"
            print(f"MOTD: {self.server_info['motd']}")

        elif command == "NICK":  # Handle nickname changes
           self.update_nickname(prefix,content)

        # Handle WHOIS response (numeric reply 311 is a common response code for WHOIS)
        elif command == "311" :
            self.handle_whois(params,content)

        # Handle LIST response (numeric reply 322 is for a channel information)
        elif command == "322":  # '322' is a numeric reply for LIST response
            self.handle_channelInfo(params)

        elif command == "353":  # '353' is a response code for the NAMES command
            self.channel_users[self.channel] = message.split(':')[-1].strip().split()  # Extract usernames
            print(f"user_list: {self.channel_users}")

        elif command == "433":
            self.handle_invalid_nickname(self.name)

        elif command == "JOIN":  # Handle user joining a channel
            self.handle_join(prefix,content)

        elif command == "PART":  # Handle user leaving a channel
            self.handle_part(prefix,params)

        elif command == "PRIVMSG":  # Handle private messages and channel messages
            self.handle_primsg(message)

    def update_nickname(self,prefix,content):
        old_nick = prefix.split('!')[0][1:]  # Old nickname
        new_nick = content.strip()  # New nickname

        print(f"{old_nick} changed their nickname to {new_nick}")

        # Update the user list for all channels the user is in
        for channel, users in self.channel_users.items():
            if old_nick in users:
                users.remove(old_nick)
                users.append(new_nick)
                print(f"Updated {channel} user list: {self.channel_users[channel]}")

    def handle_whois(self,params,content):
        nickname = params[1]  # Nickname being queried
        username = params[2]
        hostname = params[3]
        realname =  content.strip(":")
        response = f"{nickname} is {username}@{hostname} ({realname})"
        self.send_command(f"PRIVMSG {self.channel} :{response}")

    def handle_channelInfo(self,params):
        channel_name = params[1]
        user_count = params[2]
        topic = ' '.join(params[3:])
        response = f"Channel: {channel_name}, Users: {user_count}, Topic: {topic}"
        self.send_command(f"PRIVMSG {self.channel} :{response}")

    def handle_invalid_nickname(self,name):
        class NicknameError(Exception):
            # The exception to handle nickname error
            def __init__(self, message):
                    self.message = message
                    super().__init__(self.message)
        raise NicknameError(f"Error, the nickname'{name}' is already in use! Please change it and try again.")

    def handle_join(self,prefix,content):
        user = prefix.split('!')[0][1:]  # Extract the username
        channel = content  # Extract the channel name
        if channel in self.channel_users:
            self.channel_users[channel].append(user)  # Add the user to the channel's user list
        else:
            self.channel_users[channel] = [user]  # Create a new list if the channel doesn't exist
        print(f"{user} joined {channel}")

    def handle_part(self,prefix,params):
        user = prefix.split('!')[0][1:]  # Extract the username
        channel = params[0]  # Extract the channel name
        if channel in self.channel_users:
            self.channel_users[channel].remove(user)  # Remove the user from the channel's user list
        print(f"{user} left {channel}")

    def handle_primsg(self,message):
        user = message.split('!')[0][1:]  # Extract the username
        channel = message.split()[2]  # Extract the channel name
        msg_content = message.split(f"PRIVMSG {channel} :")[1]

        if msg_content.startswith("!"):  # Handle commands starting with '!'
            self.process_command(user, channel, msg_content.strip())
        else:
            if channel == self.name:  # Private message case
                random_reply = random.choice(self.responses)
                self.send_command(f"PRIVMSG {user} :{random_reply}")

    # Process specific commands received from users
    def process_command(self, user, channel, command):
        if command == "!hello":
            self.process_hello(channel,user)

        # Handle the !slap command with an optional target
        elif command.startswith("!slap"):
            parts = command.split()
            if len(parts) == 1:  # No specific user provided, randomly slap someone
                self.process_random_slap(channel,user)
            elif len(parts) == 2:  # A specific user is provided as a target
                self.process_specific_slap(parts,channel,user)

        # Handle the !whois command
        elif command.startswith("!whois"):
            self.process_whois(command,channel)

        # Handle the !list command to list all active channels
        elif command == "!list":
            self.process_list(channel,user)


    def process_hello(self,channel,user):
        if channel == self.name:  # If it's a private message
            self.send_command(f"PRIVMSG {user} :Hello {user}!")
        else:
            self.send_command(f"PRIVMSG {channel} :Hello {user}!")

    def process_random_slap(self,channel,user):
        other_users = self.get_other_users(channel, user)
        if other_users:
            target = random.choice(other_users)
            if channel == self.name:  # Private message case
                self.send_command(f"PRIVMSG {user} :You slapped {target} with a trout!")
            else:
                self.send_command(f"PRIVMSG {channel} :{user} slapped {target} with a trout!")
        else:
            if channel == self.name:  # Private message case
                self.send_command(f"PRIVMSG {user} :No one else to slap (private)!")
            else:
                self.send_command(f"PRIVMSG {channel} :No other users to slap.")

    def process_specific_slap(self,parts,channel,user):
        target = parts[1]
        other_users = self.get_other_users(channel, user)
        if target in other_users:
            if channel == self.name:  # Private message case
                self.send_command(f"PRIVMSG {user} :You slapped {target} with a trout!")
            else:
                self.send_command(f"PRIVMSG {channel} :{user} slapped {target} with a trout!")
        else:
            if channel == self.name:  # Private message case
                self.send_command(f"PRIVMSG {user} :{target} is not here, so you slap yourself!")
            else:
                self.send_command(f"PRIVMSG {channel} :{user}, {target} is not satisfied, so you slap yourself!")

    def process_whois(self,command,channel):
        parts = command.split()
        if len(parts) == 2:
            target = parts[1]
            self.send_command(f"WHOIS {target}")  # Query user info using WHOIS
        else:
            self.send_command(f"PRIVMSG {channel} :Usage: !whois <username>")

    def process_list(self,channel,user):
        if channel == self.name:  # Private message case
            self.send_command(f"PRIVMSG {user} :Listing all active channels ")
        else:
            self.send_command("LIST")  # Send the LIST command to the server

    # Fetch the list of other users in the channel, excluding the bot itself
    def get_other_users(self, channel, exclude_user):
       users=self.channel_users[self.channel]
       user_list=[]
       for user in users:
            if user != exclude_user and user != self.name and user not in user_list:
                user_list.append(user)
       return user_list

   # Connect to the server and join the channel, ensuring the bot identifies itself properly
    def connect(self):
        try:
            print(f"Connecting to server {self.server}...")
            self.socket.connect((self.server, self.port, 0, 0))  # Connect to the server with IPv6
            return True
        except (socket.error, socket.gaierror) as e:
            print(f"Network connection error: Unable to connect because the target machine actively refused the connection. Enter any key to confirm.")
            return False


    def initialize(self):
        self.send_command(f"NICK {self.name}")  # Send the bot's nickname
        self.send_command(f"USER {self.name} 0 * :{self.name}")  # Send the user information
        self.join_channel(self.channel)

    # "Send PING at regular intervals."
    def ping_server(self):
        last_message_time = time.time()  # Record the time when the bot starts

        while self.running:
            time.sleep(1)  # Check every second to see if 60 seconds have passed

            # If 60 seconds have passed since the last message was received
            if time.time() - last_message_time >= 60:
                if self.running:
                    # Get the bot's local IPv6 address and port using getsockname()
                    local_ip, local_port, *_ = self.socket.getsockname()

                    # Format the PING message with IPv6 and port information
                    ping_info = f"[{local_ip}]:{local_port}"
                    self.send_command(f"PING {ping_info}")

                    last_message_time = time.time()  # Reset the timer after sending PING

    # Main loop to continuously receive and process messages
    def run(self):
        if self.connect():
            thread = threading.Thread(target=bot.initialize)
            thread.start()
            ping_thread = threading.Thread(target=self.ping_server)
            ping_thread.start()
            while self.running:
                try:
                    # Receive data from the socket
                    response = self.socket.recv(2048).decode("utf-8")
                    if response:
                        # Split the message into lines and handle each one
                        for line in response.strip().split("\r\n"):
                            self.handle_message(line)  # Call the handle_message method for each line
                except socket.timeout:
                    print("Connection timeout.")
                    self.stop()
                    break
                except Exception as e:
                    if self.running:  # Only print errors if stopping was not intentional
                        print(f"Error occurred: {e}")
                    self.stop()
                    break
            print("Terminating bot...")
            print("Enter any button to quit.")
        else:
            self.stop()
            return

    # Stop the bot
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
    # bot.connect()
    thread = threading.Thread(target=bot.run)
    thread.start()

    # Deal with console
    try:
        while True:
            if bot.running:
                msg = input()
            else:
                print("Bot has been terminated.")
                break
    except KeyboardInterrupt:
        bot.stop()
        thread.join()
        print("\nExiting client")











# Handle incoming messages from the server
    # def handle_message(self, message):
    #     print(f"Received message: {message}")

    #     # Respond to PING to keep the connection alive
    #     if message.startswith("PING"):
    #         self.send_command(f"PONG {message.split()[1]}")

    #     # Handle nickname changes
    #     if "NICK" in message:
    #         old_nick = message.split('!')[0][1:]  # Extract the old nickname
    #         new_nick = message.split('NICK')[-1].strip()  # Extract the new nickname

    #         print(f"{old_nick} changed their nickname to {new_nick}")

    #         # Update the user list for all channels the user is in
    #         for channel, users in self.channel_users.items():
    #             if old_nick in users:
    #                 users.remove(old_nick)
    #                 users.append(new_nick)
    #                 print(f"Updated {channel} user list: {self.channel_users[channel]}")

    #     # Handle WHOIS response (numeric reply 311)
    #     elif "311" in message:
    #         parts = message.split()
    #         if len(parts) >= 8:  # Ensure the message has enough parts
    #             nickname = parts[3]  # Extract the queried nickname
    #             username = parts[4]
    #             hostname = parts[5]
    #             realname = ' '.join(parts[7:])  # Real name might be spread across multiple parts
    #             response = f"{nickname} is {username}@{hostname} ({realname})"
    #             self.send_command(f"PRIVMSG {self.channel} :{response}")

    #     # Handle LIST response (numeric reply 322)
    #     elif "322" in message:
    #         parts = message.split()
    #         if len(parts) >= 6:  # Ensure the message contains enough segments
    #             channel_name = parts[3]  # Extract channel name
    #             user_count = parts[4]  # Extract the number of users in the channel
    #             topic = ' '.join(parts[5:])  # Extract the channel topic
    #             response = f"Channel: {channel_name}, Users: {user_count}, Topic: {topic}"
    #             self.send_command(f"PRIVMSG {self.channel} :{response}")

    #     # Handle user joining a channel
    #     elif "JOIN" in message:
    #         user = message.split('!')[0][1:]  # Extract the username
    #         channel = message.split()[2]  # Extract the channel name
    #         if channel in self.channel_users:
    #             self.channel_users[channel].append(user)  # Add the user to the channel's user list
    #         else:
    #             self.channel_users[channel] = [user]  # Create a new list if the channel doesn't exist
    #         print(f"{user} joined {channel}")

    #     # Handle user leaving a channel
    #     elif "PART" in message:
    #         user = message.split('!')[0][1:]  # Extract the username
    #         channel = message.split()[2]  # Extract the channel name
    #         if channel in self.channel_users:
    #             self.channel_users[channel].remove(user)  # Remove the user from the channel's user list
    #         print(f"{user} left {channel}")

    #     # Handle private messages and channel messages
    #     elif "PRIVMSG" in message:
    #         user = message.split('!')[0][1:]  # Extract the username
    #         channel = message.split()[2]  # Extract the channel name
    #         msg_content = message.split(f"PRIVMSG {channel} :")[1]  # Extract the message content

    #         if msg_content.startswith("!"):  # Handle commands starting with '!'
    #             self.process_command(user, channel, msg_content.strip())  # Process command
    #         else:
    #             if channel == self.name:  # Handle private messages
    #                 random_reply = random.choice(self.responses)  # Random reply from facts list
    #                 self.send_command(f"PRIVMSG {user} :{random_reply}")  # Send the reply
