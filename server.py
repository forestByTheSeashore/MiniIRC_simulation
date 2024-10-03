"""
IRC Server Implementation

Author: 
Hongyu Lin
Jingran Li
Siming Lv

Date: [2024/9/20]

Description:
The python project implements a simple IRC (Internet Relay Chat) server, keep to RFC 1459 protocal standard.
The server supports message communication between clients, including private message and channel message.  It 
uses TCP socket to maintain the connection with clients, with the ablity to handle commands including NICK、USER、
JOIN、PART、PRIVMSG and PING/PONG.

Key Features:
1. use NICK and USER command to login the client
2. real-time communication between clients, including channel communication and private communication.
3. send PING message regularly to make sure the client is still in connection. If the client doesn't answer, the server will disconnect the client automatically
4. create channel dynamically, create channel when a client joins a channel that doesn't exist, delete channel when the last client leave the channel.
5. use regular expression to verify the nickname, to makesure the nick name corresponds to the stipulation. 

Usage Guide:
1. after launching, the servber will listen on 6667 port, waiting for the connection
2. the server supports clients which conform IRC protocal
3. communication works through TCP on ipv6 (or ipv4).

How to Run:
1. install python on your system
2. open the command line, change the current path to the folder's path, input "python server.py", and press enter
3. connect an IRC client to server.

Known Issues:
1. the project doesn't handle SSL/ILS, thus the communication is unencrypted
2. the server may don't completely follow all the IRC protocal specification
3. channel message can't be sent to the user successfully

Future Improvements:
1. further normalize the code logic with the IRC specification
2. implement more IRC commands
"""

import socket 
import threading
import signal
import sys
import time
import re

# Constants
HOST = '::'  # Listen on all IPv6 addresses
PORT = 6667 # Port to listen on
PING_INTERVAL = 60  # Interval (in seconds) between PING messages
PING_TIMEOUT = 120  # Timeout (in seconds) for PONG responses
BUFFER_SIZE = 1024  # Receive buffer size
NICKNAME_REGEX = re.compile(r'^[A-Za-z][A-Za-z0-9_]{2,15}$')  # Nickname must be 3-16 characters, starting with a letter

# Global data structures and locks
clients = {}  # Dictionary of connected clients
channels = {}  # Dictionary of channels and their members
clients_lock = threading.Lock()  # Lock for accessing the clients dictionary
channels_lock = threading.Lock()  # Lock for accessing the channels dictionary
server_name = "MyIRC"  # Server name for messaging
server_version = "1.0"


class Client:
    """class representing a connected client."""
    def __init__(self, socket, address):
        self.socket = socket    # Socket object for the client
        self.address = address  
        self.nickname = None
        self.username = None
        self.realname = None
        self.last_pong = time.time()  # Last time a PONG was received from the client
        self.channels = set()  # Set of channels the client is a member of
        self.lock = threading.Lock()  # Lock for thread-safe operations on this client
        self.registered = False # Flag to indicate if the client has completed 
        self.last_activity = time.time()  # Last time the client sent a message
        self.signon_time = time.time()  # Time when the client connected

    def send(self, message):
        """Send a message to the client."""
        try:
            with self.lock:
                self.socket.sendall(message.encode('utf-8'))
                self.last_activity = time.time()
        except Exception as e:
            print(f"Error sending message to {self.nickname}: {e}")

    def close(self, reason="Disconnected"):
        """Close the client's connection and remove them from all channels."""
        try:
            self.socket.close()
            self.last_activity = time.time()
        except:
            pass
        if self.nickname:
            with clients_lock:
                if self.nickname in clients:
                    del clients[self.nickname]
            leave_all_channels(self)
            broadcast(f":server NOTICE * :{self.nickname} has left the chat room ({reason})\r\n", exclude=self)
            print(f"{self.nickname} has disconnected: {reason}")

def broadcast(message, exclude=None):
    """Broadcast a message to all clients except the excluded one."""
    with clients_lock:
        for client in clients.values():
            if client != exclude:
                client.send(message)

def leave_all_channels(client):
    """Remove the client from all channels they are a part of and notify others."""
    with channels_lock:
        for channel in list(client.channels):
            if channel in channels:
                channels[channel].discard(client.nickname)
                if not channels[channel]:
                    del channels[channel]
                else:
                    broadcast(f":server NOTICE {channel} :{client.nickname} has left the channel\r\n", exclude=client)
            client.channels.discard(channel)

def validate_nickname(nickname):
    """Validate the nickname according to the defined regex."""
    return NICKNAME_REGEX.match(nickname) is not None

def handle_client(client_socket, addr):
    """Handle communication with a connected client."""
    client = Client(client_socket, addr)
    
    # Server allows and remembers a new HexChat client connection
    print(f"Client connected: {addr}")

    # Start PING thread
    ping_thread = threading.Thread(target=ping_client, args=(client,), daemon=True)
    ping_thread.start()

    # Receive and process data from the client
    # The client should send a message based on the IRC protocol.
    try:
        while True:
            try:
                data = client.socket.recv(BUFFER_SIZE)
                if not data:
                    print(f"No data received. Closing connection for {client.nickname or 'Guest'}")
                    break
                messages = data.decode('utf-8').strip().split('\r\n')
                for message in messages:
                    if message:
                        process_command(client, message)
            except socket.timeout:
                print(f"Client {client.nickname} timed out due to inactivity.")
                break
            except Exception as e:
                print(f"Error receiving data from {client.nickname}: {e}")
                break
    finally:
        client.close()

def process_command(client, message):
    """Process and handle IRC commands received from a client."""
    print(f"Received from {client.nickname or 'Guest'}: {message}")
    parts = message.split(' ')
    command = parts[0].upper()
    print(f"Command: {command}")

    # Dispatch command to specific handler
    if command == 'CAP':
        handle_cap_command(client, parts)
    elif command == "NICK":
        handle_nick_command(client, parts)
    elif command == "USER":
        handle_user_command(client, parts)
    elif command == "PONG":
        handle_pong_command(client)
    elif command == "JOIN":
        handle_join_command(client, parts)
    elif command == "PART":
        handle_part_command(client, parts)
    elif command == "PRIVMSG":
        handle_privmsg_command(client, parts)
    elif command == "NAMES":
        handle_names_command(client, parts)
    elif command == "QUIT":
        handle_quit_command(client, parts)
    elif command == "WHOIS":
        handle_whois_command(client, parts)
    else:
        handle_unknown_command(client, command)

def handle_nick_command(client, parts):
    if len(parts) < 2:
        client.send(f":{server_name} 431 * :No nickname given\r\n")
        return
    new_nick = parts[1]
    if not validate_nickname(new_nick):
        client.send(f":{server_name} 432 * {new_nick} :Erroneous nickname\r\n")
        return
    with clients_lock:
        if new_nick in clients:
            client.send(f":{server_name} 433 * {new_nick} :Nickname is already in use\r\n")
            return
        old_nick = client.nickname
        client.nickname = new_nick
        clients[new_nick] = client
        if old_nick and old_nick in clients:
            del clients[old_nick]
    client.send(f":{server_name} 001 {new_nick} :Nickname set to {new_nick}\r\n")
    print(f"Client set nickname to {new_nick}")

def handle_user_command(client, parts):
    if len(parts) < 5:
        client.send(f":{server_name} 461 {client.nickname} USER :Not enough parameters\r\n")
        return
    client.username = parts[1]
    client.realname = parts[4].lstrip(':')
    print(f"Client {client.nickname} set username to {client.username} and realname to {client.realname}")
    if client.nickname and client.username and not client.registered:
        client.registered = True
        send_registration_welcome(client)

def handle_pong_command(client):
    client.last_pong = time.time()
    print(f"Received PONG from {client.nickname}")

def handle_join_command(client, parts):
    if len(parts) < 2:
        client.send(f":{server_name} 461 {client.nickname} JOIN :Not enough parameters\r\n")
        return
    channel_name = parts[1]
    if not channel_name.startswith("#"):
        client.send(f":{server_name} 476 {client.nickname} {channel_name} :Bad channel mask\r\n")
        return
    join_channel(client, channel_name)

def handle_part_command(client, parts):
    if len(parts) < 2:
        client.send(f":{server_name} 461 {client.nickname} PART :Not enough parameters\r\n")
        return
    channel_name = parts[1]
    part_channel(client, channel_name)

def handle_privmsg_command(client, parts):
    if len(parts) < 3:
        client.send(f":{server_name} 461 {client.nickname} PRIVMSG :Not enough parameters\r\n")
        return
    target, msg = parts[1], parts[2].lstrip(':')
    if target.startswith("#"):
        send_channel_message(client, target, msg)
    else:
        send_private_message(client, target, msg)

def handle_quit_command(client, parts):
    reason = parts[1].lstrip(':') if len(parts) > 1 else "Client Quit"
    client.send(f":{server_name} QUIT :{client.nickname} has quit ({reason})\r\n")
    client.close(reason)

def handle_whois_command(client, parts):
    if len(parts) < 2:
        client.send(f":{server_name} 431 {client.nickname} :No nickname given\r\n")
    else:
        handle_whois(client, parts[1:])

def handle_unknown_command(client, command):
    client.send(f":{server_name} 421 {client.nickname} {command} :Unknown command\r\n")

def send_registration_welcome(client):
    client.send(f":{server_name} 001 {client.nickname} :Welcome to the IRC network, {client.nickname}\r\n")
    client.send(f":{server_name} 002 {client.nickname} :Your host is {server_name}, running version {server_version}\r\n")
    client.send(f":{server_name} 003 {client.nickname} :This server is created sometime\r\n")
    client.send(f":{server_name} 004 {client.nickname} {server_name} {server_version} o o\r\n")
    client.send(f":{server_name} 251 {client.nickname} There are {len(clients)} users and 1 server\r\n")
    broadcast(f":server NOTICE * :{client.nickname} has joined the chat room\r\n", exclude=client)

def handle_cap_command(client, parts):
    """Handle the cap command, to tell the client the capability the server has."""
    if not parts:
        return

    subcommand = parts[1].upper()
    if subcommand == "LS":
        # List the server-supported capabilities
        capabilities = "multi-prefix sasl"
        client.send(f":{server_name} CAP {client.nickname} LS :{capabilities}\r\n")
    elif subcommand == "REQ":
        # Client requests to enable certain capabilities
        requested_caps = parts[2].split()
        # Reject all requested capabilities by sending a NAK response
        rejected_caps = " ".join(requested_caps)
        client.send(f":{server_name} CAP {client.nickname} NAK :{rejected_caps}\r\n")
    elif subcommand == "END":
        # End CAP negotiation
        client.send(f":{server_name} CAP {client.nickname} END\r\n")
    else:
        # Unknown CAP subcommand
        client.send(f":{server_name} 410 {client.nickname} :Invalid CAP subcommand\r\n")

def join_channel(client, channel_name):
    """ To handle the operation of joining the object channel after "JOIN" is received.
    Add the client to a channel and notify other members."""
    with channels_lock:
        if channel_name not in channels:
            channels[channel_name] = set()
        channels[channel_name].add(client.nickname)  # Add nickname instead of client object
    client.channels.add(channel_name)

    # Send JOIN confirmation message
    client.send(f":{client.nickname}!{client.username}@{client.address[0]} JOIN {channel_name}\r\n")

    # Send channel topic (if any)
    topic = "No topic is set"  # Placeholder for channel topic
    client.send(f":{server_name} 332 {client.nickname} {channel_name} :{topic}\r\n")

    # Send NAMES list
    user_list = ' '.join(channels[channel_name])
    client.send(f":{server_name} 353 {client.nickname} = {channel_name} :{user_list}\r\n")
    client.send(f":{server_name} 366 {client.nickname} {channel_name} :End of /NAMES list.\r\n")

    # Notify other members in the channel
    broadcast(f":{client.nickname}!{client.username}@{client.address[0]} JOIN {channel_name}\r\n", exclude=client)
    print(f"{client.nickname} joined channel {channel_name}")

    # Print the client in the current channel
    print(f"Current channel {channel_name}: {channels[channel_name]}")

def handle_names_command(client, parts):
    """To handle the operation of sending each name of the current channel's users after "NAMES" is received.
    Send message of the user's name list in the chatroom, including users in specific channel."""
    if len(parts) < 2:
        # if no channels, return all the user lists
        for channel in channels:
            user_list = ' '.join([user.nickname for user in channels[channel]])
            client.send(f":{server_name} 353 {client.nickname} = {channel} :{user_list}\r\n")
        client.send(f":{server_name} 366 {client.nickname} * :End of /NAMES list.\r\n")
    else:
        channel = parts[1]
        if channel in channels:
            user_list = ' '.join([user.nickname for user in channels[channel]])
            client.send(f":{server_name} 353 {client.nickname} = {channel} :{user_list}\r\n")
            client.send(f":{server_name} 366 {client.nickname} {channel} :End of /NAMES list.\r\n")
        else:
            client.send(f":{server_name} 403 {client.nickname} {channel} :No such channel\r\n")


def part_channel(client, channel_name):
    """To handle the operation of leaving the object channel after "PART" is received.
    Remove the client from a channel and notify other members."""
    with channels_lock:
        if channel_name in channels and client.nickname in channels[channel_name]:
            # Notify other members in the channel
            broadcast(f":{client.nickname}!{client.username}@{client.address[0]} PART {channel_name}\r\n",
                      exclude=client)

            # Remove the client from the channel
            channels[channel_name].discard(client.nickname)
            if not channels[channel_name]:
                del channels[channel_name]
            client.channels.discard(channel_name)

            # Send PART confirmation message to the client
            client.send(f":{client.nickname}!{client.username}@{client.address[0]} PART {channel_name}\r\n")
            print(f"{client.nickname} left channel {channel_name}")
        else:
            client.send(f":{server_name} 442 {client.nickname} {channel_name} :You're not on that channel\r\n")

def send_channel_message(sender, channel_name, message):
    """To handle the operation of sending message to the object channel after "PRIVMSG" is received and the second argument start with "#".
    Send a message to all members of a channel."""
    with channels_lock:
        if channel_name not in channels:
            sender.send(f":{server_name} 403 {sender.nickname} {channel_name} :No such channel\r\n")
            return
        if sender.nickname not in channels[channel_name]:  # 检查发送者是否在频道中
            sender.send(f":{server_name} 442 {sender.nickname} {channel_name} :You're not on that channel\r\n")
            return
        members = channels[channel_name].copy()

    for member_nick in members:
        if member_nick == sender.nickname:
            continue
        with clients_lock:
            target_client = clients.get(member_nick)
            if target_client:
                try:
                    target_client.send(f":{sender.nickname} PRIVMSG {channel_name} :{message}\r\n")
                except Exception as e:
                    print(f"Error sending channel message to {member_nick}: {e}")
    print(f"{sender.nickname} sent message to {channel_name}: {message}")

def send_private_message(sender, target_nick, message):
    """To handle the operation of sending private message to the object client after "PRIVMSG" is received.
    Send a private message to a specific client."""
    with clients_lock:
        target_client = clients.get(target_nick)
    if target_client:
        try:
            target_client.send(f"Chat from {sender.nickname}: {message}\r\n")
            sender.send(f"Chat to {target_nick}: {message}\r\n")
            print(f"{sender.nickname} sent private message to {target_nick}: {message}")
        except Exception as e:
            print(f"Error sending private message to {target_nick}: {e}")
    else:
        sender.send(f"ERROR :{target_nick} is offline\r\n")

def ping_client(client):
    """Periodically send PING messages to the client and check for responses in order to insure the connection is maintained."""
    while True:
        time.sleep(PING_INTERVAL)
        try:
            current_time = time.time()
            if current_time - client.last_pong > PING_TIMEOUT:
                print(f"{client.nickname} did not respond to PING, disconnecting...")
                client.send(f":{server_name} ERROR :Closing Link: {client.nickname} (Ping timeout)\r\n")
                client.close("Ping timeout")
                break
            client.send("PING :server\r\n")
            print(f"Sent PING to {client.nickname}")
        except Exception as e:
            print(f"Error in ping_thread for {client.nickname}: {e}")
            client.close("Ping thread error")
            break

def handle_whois_command(client, params):
    """Handle the WHOIS command when 'WHOIS' is received."""
    if len(params) < 1:
        client.send(f":{server_name} 431 {client.nickname} :No nickname given\r\n")
        return

    target_nick = params[0]
    with clients_lock:
        target_client = clients.get(target_nick)

    if not target_client:
        client.send(f":{server_name} 401 {client.nickname} {target_nick} :No such nick/channel\r\n")
        return

    # Send user information
    client.send(f":{server_name} 311 {client.nickname} {target_client.nickname} {target_client.username} "
                f"{target_client.address[0]} * :{target_client.realname}\r\n")

    # Send server information
    client.send(f":{server_name} 312 {client.nickname} {target_client.nickname} {server_name} :Server Info\r\n")

    # Send channel list
    channels_list = ' '.join(target_client.channels)
    client.send(f":{server_name} 319 {client.nickname} {target_client.nickname} :{channels_list}\r\n")

    # Send idle time and signon time
    idle_time = int(time.time() - target_client.last_activity)
    signon_time = int(target_client.signon_time)
    client.send(f":{server_name} 317 {client.nickname} {target_client.nickname} {idle_time} {signon_time} "
                f":seconds idle, signon time\r\n")

    # End of WHOIS
    client.send(f":{server_name} 318 {client.nickname} {target_client.nickname} :End of /WHOIS list.\r\n")

def main():
    """Initialize and start the server, accepting and handling client connections."""
    global server_socket
    server_socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(5)
    server_socket.settimeout(1.0)  # Set timeout to periodically check for signals

    print(f"Server activated on {HOST}:{PORT}, waiting for connections...")

    try:
        while True:
            try:
                client_socket, addr = server_socket.accept()
                client_socket.settimeout(60)  # Set to blocking mode
                client_thread = threading.Thread(target=handle_client, args=(client_socket, addr), daemon=True)
                client_thread.start()
            except socket.timeout:
                continue
            except Exception as e:
                print(f"Error accepting connections: {e}")
    finally:
        server_socket.close()

# The main entrance of the server program
if __name__ == "__main__":
    main()
