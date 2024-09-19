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

    # Handle received messages
    def handle_message(self, message):
        # Keeping the connection to miniircd alive, and managing it efficiently
        print(f"Received message: {message}")
        if message.startswith("PING"):
            self.send_command(f"PONG {message.split()[1]}")  #Respond to the server's PING

        elif "PRIVMSG" in message:
            user = message.split('!')[0][1:]  # Get the username
            channel = message.split()[2]
            msg_content = message.split(f"PRIVMSG {channel} :")[1]

            if msg_content.startswith("!"):
                self.process_command(user, channel, msg_content.strip())
            else:
                # Respond to private messages with a random reply
                if channel == self.name:  # If the channel name is the bot's name, it's a private message
                    random_reply = random.choice(self.responses)
                    self.send_command(f"PRIVMSG {user} :{random_reply}")

    # Handle specific commands
    def process_command(self, user, channel, command):
        if command == "!hello":
            self.send_command(f"PRIVMSG {channel} :Hello {user}!")

        elif command.startswith("!slap"):
            other_users = self.get_other_users(channel, user)
            print(other_users)
            if other_users:
                target = random.choice(other_users)

                self.send_command(f"PRIVMSG {channel} :{user} slapped {target} with a trout!")
            else:
                self.send_command(f"PRIVMSG {channel} :No other users to slap.")

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
