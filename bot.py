"""
IRC Bot Client

Author:
Hongyu Lin
Jingran Li
Siming Lv 
Chengyang Zhu 
Zijian Zhou

Date: [2024/10/4]

Description:
This Python script implements an IRC (Internet Relay Chat) bot using sockets and threading. 
The bot connects to an IRC server, joins a specified channel, and interacts with users by responding to specific commands or private messages.

Key Features:
1. The bot connects to an IRC server using IPv6 and enters the target channel.
2. The bot can handle the following commands:
   - '!hello' command will make the bot say hello to the user.
   - '!slap' command will simulate an interaction, randomly 'slap' another user in a channel. Additionally, the !slap command can accept a parameter to specifically slap a particular user.
   - '!list' command is used to display all the channels on the current server, along with relevant information such as the number of users and the channel topic.
   - '!whois' command is used to query detailed information about a specific user. The usage is '!whois [parameter]'.
3. The bot can randomly reply with an interesting fact or other replies.
4. The bot can reply to PING commands from the server to ensure the connection stays active.
5. The bot can send a PING command to the server at regular intervals to implement a heartbeat mechanism.
6. The bot can use the 'NAMES' command to fetch the user list in the current channel, ensuring it won't 'slap' itself.
7. It can handle situations like connection timeouts and other exceptions.

Usage Instructions:
When running the bot script, use the command line to input the host, port, bot name, and channel to join:
python bot.py --host <server address> --port <port> --name <bot name> --channel <channel>
Example: python bot.py --host fec0:1337::17 --port 6667 --name SuperBot --channel hello
NOTICE!: Do not use "#" when entering the bot name. eg: use "superbot" instead of "#superbot".
The bot will continue running and listening on the target server, and you can stop the bot using the 'ctrl + c' command.

Command-Line Arguments:
1. '--host': Address of the IRC server, defaulted to 'fec0:1337::17' (IPv6).
2. '--port': The port number for the server, defaulting to 6667.
3. '--name': The nickname of the bot, defaulted to 'SuperBot'.
4. '--channel': The channel to join, defaulted to '#hello'. If a channel name is passed without the '#' prefix, the bot automatically adds it.

Dependencies:
The bot script uses only the standard Python library: 'socket', 'random', 'argparse', and 'threading', 'os', 'time'. Please ensure Python3 is installed on your system.
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
        self.server = host  # Set the server address
        self.port = port  # Set the server port
        self.name = name  # Set the bot's nickname
        self.channel = channel  # Set the channel to join
        self.socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)  # Use IPv6 socket
        # Set a reasonable timeout and handle errors
        self.socket.settimeout(300)  # Timeout for socket operations set to 300 seconds
        self.running = True  # Used to control the main loop, indicates if the bot is running
        self.responses = self.load_facts()  # Load predefined responses from a file
        # Initialize a dictionary to store users in each channel
        self.channel_users = {}  # To hold user lists for different channels
        self.server_info = {}  # To store server-related information

    # Load facts from a file to be used as responses
    def load_facts(self):
        script_path = os.path.abspath(__file__)  # Get the absolute path of the current script
        script_dir = os.path.dirname(script_path)  # Get the directory of the script
        
        os.chdir(script_dir)  # Change working directory to the script directory
        facts_file = "facts.txt"  # Define the name of the facts file
        facts = []  # Initialize an empty list to store facts
        if os.path.exists(facts_file):  # Check if the facts file exists
            with open(facts_file, "r", encoding="utf-8") as f:  # Open the facts file
                facts = f.read().splitlines()  # Read the lines into the facts list
        else:
            print(f"{facts_file} File not found.")  # Print an error message if the file does not exist
        return facts  # Return the list of facts

    # Send a command to the IRC server
    def send_message(self, command):
        if self.socket:  # Check if the socket is still open
            print(f"Sending: {command}")  # Print the command being sent
            self.socket.send((command + "\r\n").encode())  # Send the command to the server
        else:
            print(f"Cannot send: {command} as the socket has closed.")  # Print an error message if the socket is closed

    # Run a thread to send the command
    def send_command(self, command):
        send_thread = threading.Thread(target=self.send_message, args=(command,))  # Create a new thread to send the message
        send_thread.start()  # Start the thread

    # Join a channel and fetch the user list
    def join_channel(self, channel):
        self.send_command(f"JOIN {channel}")  # Send the command to join the specified channel
        self.send_command(f"NAMES {channel}")  # Send NAMES command to get user list


    # Handle incoming messages from the server
    def handle_message(self, message):
        print(f"Received message: {message}")  # Print the received message for debugging
        if message.startswith("PING"):  # Handle server PING
            self.send_command(f"PONG {message.split()[1]}")  # Respond to the PING to keep the connection alive
            return  # Exit the method after handling PING
        elif message.startswith("PONG"):
            return  # Exit if it's a PONG response

        components = message.split()  # Split the message into components
        prefix = components[0]  # The prefix (usually the sender's info)
        command = components[1]  # The command type (e.g., NICK, JOIN)
        params = components[2:]  # Any additional parameters in the message
        content = components[-1]  # The content (last part of the message)

        user = prefix.split('!')[0][1:]  # Extract the username from the prefix
        if user == self.name or command == "NOTICE":  # Ignore messages from the bot itself or server notice
            return  # Exit if the message is from the bot or a notice
        print(f"User: {user}, Command: {command}, Params: {params}, Content: {content}")  # Debugging output

        # Handle various command responses from the server
        if command == "001":  # Welcome message
            self.server_info["welcome"] = message.split(":", 2)[-1]  # Store welcome message
            print(f"Welcome: {self.server_info['welcome']}")  # Print welcome message
        elif command == "002":  # Host information
            self.server_info["host"] = message.split(":", 2)[-1]  # Store host info
            print(f"Host: {self.server_info['host']}")  # Print host info
        elif command == "003":  # Server creation information
            self.server_info["creation"] = message.split(":", 2)[-1]  # Store server creation info
            print(f"Creation: {self.server_info['creation']}")  # Print creation info
        elif command == "004":  # Server and version details
            self.server_info["version"] = params[1:]  # Store server name and version
            print(f"Version: {self.server_info['version']}")  # Print server version
        elif command == "251":  # Server user statistics
            self.server_info["user_stats"] = message.split(":", 2)[-1]  # Store user statistics
            print(f"User stats: {self.server_info['user_stats']}")  # Print user stats
        elif command == "422":  # MOTD missing
            self.server_info["motd"] = "MOTD is missing"  # Handle missing MOTD
            print(f"MOTD: {self.server_info['motd']}")  # Print MOTD info

        # Handle nickname changes
        elif command == "NICK":  
            self.update_nickname(prefix, content)  # Update nickname

        # Handle WHOIS response (numeric reply 311 is a common response code for WHOIS)
        elif command == "311":
            self.handle_whois(params, content)  # Process WHOIS response

        # Handle LIST response (numeric reply 322 is for a channel information)
        elif command == "322":  # '322' is a numeric reply for LIST response
            self.handle_channelInfo(params)  # Process channel info response

        # Handle NAMES command response
        elif command == "353":  # '353' is a response code for the NAMES command
            self.channel_users[self.channel] = message.split(':')[-1].strip().split()  # Extract usernames
            print(f"user_list: {self.channel_users}")  # Print the user list for the channel

        # Handle error for non-existent users
        elif command == "401" and params[0] == self.name:
            self.send_command(f"PRIVMSG {self.channel} :Error: the user({params[1]}) you looking for does not exist.")

        # Handle invalid nickname error
        elif command == "433":
            self.handle_invalid_nickname(self.name)  # Handle nickname in use error

        # Handle user joining a channel
        elif command == "JOIN":  
            self.handle_join(prefix, content)  # Process user joining a channel

        # Handle user leaving a channel
        elif command == "PART":  
            self.handle_part(prefix, params)  # Process user leaving a channel

        # Handle private messages and channel messages
        elif command == "PRIVMSG":  
            self.handle_primsg(message)  # Process private or channel messages

    # Update nickname in the user list
    def update_nickname(self, prefix, content):
        old_nick = prefix.split('!')[0][1:]  # Old nickname
        new_nick = content.strip()  # New nickname

        print(f"{old_nick} changed their nickname to {new_nick}")  # Print nickname change

        # Update the user list for all channels the user is in
        for channel, users in self.channel_users.items():
            if old_nick in users:  # Check if the old nickname exists in the channel user list
                users.remove(old_nick)  # Remove the old nickname
                users.append(new_nick)  # Add the new nickname
                print(f"Updated {channel} user list: {self.channel_users[channel]}")  # Print updated user list

    # Handle WHOIS response
    def handle_whois(self, params, content):
        nickname = params[1]  # Nickname being queried
        username = params[2]  # Username of the queried nickname
        hostname = params[3]  # Hostname of the queried nickname
        realname = content.strip(":")  # Real name of the user
        response = f"{nickname} is {username}@{hostname} ({realname})"  # Format WHOIS response
        self.send_command(f"PRIVMSG {self.channel} :{response}")  # Send WHOIS response to the channel

    # Handle channel information response
    def handle_channelInfo(self, params):
        channel_name = params[1]  # Name of the channel
        user_count = params[2]  # Number of users in the channel
        # Check if topic is provided
        if len(params) > 4:
            topic = ' '.join(params[3:])  # Extract the topic from the parameters
        else:
            topic = "(No topic)"  # Default if no topic is set
        response = f"Channel: {channel_name}, Users: {user_count}, Topic: {topic}"  # Format channel info response
        self.send_command(f"PRIVMSG {self.channel} :{response}")  # Send channel info to the channel

    # Handle invalid nickname error
    def handle_invalid_nickname(self, name):
        class NicknameError(Exception):
            # The exception to handle nickname error
            def __init__(self, message):
                self.message = message  # Store the error message
                super().__init__(self.message)  # Call the base class constructor

        raise NicknameError(f"Error, the nickname '{name}' is already in use! Please change it and try again.")  # Raise the nickname error

    # Handle user joining a channel
    def handle_join(self, prefix, content):
        user = prefix.split('!')[0][1:]  # Extract the username
        channel = content  # Extract the channel name
        if channel in self.channel_users:  # Check if the channel exists
            self.channel_users[channel].append(user)  # Add the user to the channel's user list
        else:
            self.channel_users[channel] = [user]  # Create a new list if the channel doesn't exist
        print(f"{user} joined {channel}")  # Print join message

    # Handle user leaving a channel
    def handle_part(self, prefix, params):
        user = prefix.split('!')[0][1:]  # Extract the username
        if params:  # Check if params are provided
            channel = params[0]  # Extract the channel name
            if channel in self.channel_users:  # Check if the channel exists
                self.channel_users[channel].remove(user)  # Remove the user from the channel's user list
            print(f"{user} left {channel}")  # Print leave message
        else:
            print(f"Error: No channel specified in PART command from {user}")  # Print error message if no channel is specified

    # Handle private messages sent by users
    def handle_primsg(self, message):
        # Extract the username from the message
        user = message.split('!')[0][1:]  
        # Extract the channel name from the message
        channel = message.split()[2]  
        # Extract the content of the message after "PRIVMSG <channel> :"
        msg_content = message.split(f"PRIVMSG {channel} :")[1]
        # Print the user, channel, and message content for debugging
        print(f"User: {user}, Channel: {channel}, Message: {msg_content}")

        # Check if the message starts with '!', indicating a command
        if msg_content.startswith("!"):  
            self.process_command(user, channel, msg_content.strip())  # Process the command
        else:
            # If the message is a private message to the bot
            if channel == self.name:  
                # Select a random reply from predefined responses
                random_reply = random.choice(self.responses)
                print(f"Random reply: {random_reply}")
                # Send the random reply back to the user
                self.send_command(f"PRIVMSG {user} :{random_reply}")

    # Process specific commands received from users
    def process_command(self, user, channel, command):
        # Handle the !hello command
        if command == "!hello":
            self.process_hello(channel, user)

        # Handle the !slap command with an optional target
        elif command.startswith("!slap"):
            parts = command.split()  # Split the command into parts
            if len(parts) == 1:  # No specific user provided, randomly slap someone
                self.process_random_slap(channel, user)
            elif len(parts) == 2:  # A specific user is provided as a target
                self.process_specific_slap(parts, channel, user)
            else:
                # Provide usage instructions if the command format is incorrect
                if channel == self.name:
                    self.send_command(f"PRIVMSG {user} :Usage: !slap <username> or !slap(to slap a random user)")
                else:
                    self.send_command(f"PRIVMSG {channel} :Usage: !slap <username> or !slap(to slap a random user)")

        # Handle the !whois command
        elif command.startswith("!whois"):
            # Send a message if the command is sent in private chat
            if channel == self.name:
                self.send_command(f"PRIVMSG {user} :Usage: !whois should be sent in channel, not in private chat.")
            else:
                self.process_whois(command, channel)

        # Handle the !list command to list all active channels
        elif command == "!list":
            self.process_list(channel, user)

    # Process "!hello" command sent by users
    def process_hello(self, channel, user):
        # If it's a private message, greet the user privately
        if channel == self.name:  
            self.send_command(f"PRIVMSG {user} :Hello {user}!")
        else:
            # Greet the user in the channel
            self.send_command(f"PRIVMSG {channel} :Hello {user}!")
            
    # Process random "!slap" command sent by users
    def process_random_slap(self, channel, user):
        # Get a list of other users in the channel
        other_users = self.get_other_users(user)
        if other_users:
            # Randomly select a user to slap
            target = random.choice(other_users)
            if channel == self.name:  # Private message case
                self.send_command(f"PRIVMSG {user} :You slapped {target} with a trout! Even if I don't know why you slap a random person in the private chat. :(")
            else:
                self.send_command(f"PRIVMSG {channel} :{user} slapped {target} with a trout!")
        else:
            # If no other users are present, inform the user
            if channel == self.name:  # Private message case
                self.send_command(f"PRIVMSG {user} :No one else to slap (private)!")  # No one to slap
            else:
                self.send_command(f"PRIVMSG {channel} :No other users to slap.")  # No one to slap in the channel

    # Process specific "!slap" command sent by users
    def process_specific_slap(self, parts, channel, user):
        # Target the specified user from the command parts
        target = parts[1]
        # Get a list of other users in the channel
        other_users = self.get_other_users(user)
        if target in other_users:
            if channel == self.name:  # Private message case
                self.send_command(f"PRIVMSG {user} :You slapped {target} in a private chat? What a person you are!")
            else:
                self.send_command(f"PRIVMSG {channel} :{user} slapped your target:{target} with a trout!")
        else:
            # Handle cases where the target is not valid
            if channel == self.name:  # Private message case
                if target == user:  # User is slapping themselves
                    self.send_command(f"PRIVMSG {user} :{user}, I don't know why, but you slapped yourself, so sad.")
                elif target == self.name:  # User is trying to slap the bot
                    self.send_command(f"PRIVMSG {user} :{user}, you want to slap me? No way, I just dodged it~ :)")
                else:  # Target not found
                    self.send_command(f"PRIVMSG {user} :I cannot find {target}, so you slap yourself!")
            elif target == self.name:  # User is trying to slap the bot
                self.send_command(f"PRIVMSG {channel} :{user}, you want to slap me? No way, I just dodged it~ :)")
            elif target == user:  # User is slapping themselves
                self.send_command(f"PRIVMSG {channel} :{user}, I don't know why, but you slapped yourself, so sad.")
            else:  # Target not found
                self.send_command(f"PRIVMSG {channel} :{target} is not here, so you slap yourself!")

    # Process "!whois" command sent by users
    def process_whois(self, command, channel):
        # Split the WHOIS command into parts
        parts = command.split()
        if len(parts) == 2:
            target = parts[1]  # Get the target username
            self.send_command(f"WHOIS {target}")  # Query user info using WHOIS
        else:
            self.send_command(f"PRIVMSG {channel} :Usage: !whois <username>")  # Provide usage instructions
    # Process "!list" command sent by users
    def process_list(self, channel, user):
        # If it's a private message, list active channels privately
        if channel == self.name:  
            self.send_command(f"PRIVMSG {user} :Listing all active channels ")
        else:
            self.send_command("LIST")  # Send the LIST command to the server

    # Fetch the list of other users in the channel, excluding the bot itself
    def get_other_users(self, exclude_user):
        users = self.channel_users[self.channel]  # Get users in the current channel
        user_list = []  # List to store users excluding the bot
        for user in users:
            if user != exclude_user and user != self.name and user not in user_list:
                user_list.append(user)  # Add user to the list if conditions are met
        return user_list

    # Connect to the server and join the channel, ensuring the bot identifies itself properly
    def connect(self):
        try:
            print(f"Connecting to server {self.server}...")
            # Connect to the server with IPv6
            self.socket.connect((self.server, self.port, 0, 0))  
            return True  # Connection successful
        except (socket.error, socket.gaierror) as e:
            # Handle connection errors
            print(f"Network connection error: Unable to connect because the target machine actively refused the connection. Enter any key to confirm.")
            return False  # Connection failed

    # Initialize bot's information
    def initialize(self):
        # Send the bot's nickname and user information to the server
        self.send_command(f"NICK {self.name}")  
        self.send_command(f"USER {self.name} 0 * :{self.name}")  
        self.join_channel(self.channel)  # Join the specified channel

    # "Send PING at regular intervals."
    def ping_server(self):
        last_message_time = time.time()  # Record the time when the bot starts

        while self.running:  # Loop while the bot is running
            time.sleep(1)  # Check every second to see if 60 seconds have passed

            # If 60 seconds have passed since the last message was received
            if time.time() - last_message_time >= 60:
                if self.running:
                    # Get the bot's local IPv6 address and port using getsockname()
                    local_ip, local_port, *_ = self.socket.getsockname()

                    # Format the PING message with IPv6 and port information
                    ping_info = f"[{local_ip}]:{local_port}"  
                    self.send_command(f"PING {ping_info}")  # Send PING to the server

                    last_message_time = time.time()  # Reset the timer after sending PING

    # Main loop to continuously receive and process messages
    def run(self):
        if self.connect():  # Attempt to connect to the server
            thread = threading.Thread(target=bot.initialize)  # Initialize the bot in a separate thread
            thread.start()
            ping_thread = threading.Thread(target=self.ping_server)  # Start the PING server thread
            ping_thread.start()
            while self.running:  # Main loop while the bot is running
                try:
                    # Receive data from the socket
                    response = self.socket.recv(2048).decode("utf-8")  
                    if response:
                        # Split the message into lines and handle each one
                        for line in response.strip().split("\r\n"):
                            self.handle_message(line)  # Call the handle_message method for each line
                except socket.timeout:
                    print("Connection timeout.")  # Handle connection timeout
                    self.stop()  # Stop the bot
                    break
                except Exception as e:
                    if self.running:  # Only print errors if stopping was not intentional
                        print(f"Error occurred: {e}")
                    self.stop()  # Stop the bot on error
                    break
            print("Terminating bot...")  # Inform that the bot is terminating
            print("Enter any button to quit.")  # Prompt for exit
        else:
            self.stop()  # Stop the bot if connection failed
            return

    # Stop the bot
    def stop(self):
        self.running = False  # Mark the bot as not running
        self.socket.close()  # Close the socket connection


# Use argparse to parse command-line arguments
if __name__ == "__main__":  # Check if the script is being run as the main program
    # Create an ArgumentParser object to handle command-line arguments
    parser = argparse.ArgumentParser(description="IRC bot client")
    # Add an argument for the server address, defaulting to "fec0:1337::17" (IPv6 localhost)
    parser.add_argument("--host", type=str, default="fec0:1337::17", help="Server address")
    # Add an argument for the server port, defaulting to 6667 (common IRC port)
    parser.add_argument("--port", type=int, default=6667, help="Server port")
    # Add an argument for the bot's nickname, defaulting to "SuperBot"
    parser.add_argument("--name", type=str, default="SuperBot", help="Bot's nickname")
    # Add an argument for the channel to join, defaulting to "#hello"
    parser.add_argument("--channel", type=str, default="#hello", help="Channel to join")

    # Parse the command-line arguments provided by the user
    args = parser.parse_args()

    # Ensure the channel name starts with '#' for proper IRC formatting
    if not args.channel.startswith('#'):
        args.channel = f'#{args.channel}'  # Prepend '#' if missing

    # Create an instance of the IRCBot class with the parsed arguments
    bot = IRCBot(args.host, args.port, args.name, args.channel)
    
    # Start the bot's run method in a separate thread to allow for concurrent execution
    thread = threading.Thread(target=bot.run)
    thread.start()

    # Handle console input for user interaction with the bot
    try:
        while True:  # Infinite loop to keep the program running
            if bot.running:  # Check if the bot is still running
                msg = input()  # Wait for user input in the console
            else:
                print("Bot has been terminated.")  # Inform user if the bot is no longer running
                break  # Exit the loop if the bot has stopped
    except KeyboardInterrupt:  # Handle Ctrl+C interruption gracefully
        bot.stop()  # Call the stop method on the bot to terminate it
        thread.join()  # Wait for the bot thread to finish execution
        print("\nExiting client")  # Inform the user that the client is exiting
