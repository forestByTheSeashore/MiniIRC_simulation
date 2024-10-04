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
import asyncio
import socket
import time
import re
import psutil
import threading

# Constants
HOST = '::'  # The server listens on all IPv6 addresses, allowing for wider connectivity across different networks.
PORT = 6667  # Port required.
PORT = 6667  # Regular PING messages are sent every 60 seconds to check if the client is still responsive.
PING_INTERVAL = 60  # Interval (in seconds) between PING messages
PING_TIMEOUT = 120  # Timeout (in seconds) for PONG responses
RES_TIMEOUT = 60
BUFFER_SIZE = 1024  # Receive buffer size
NICKNAME_REGEX = re.compile(r'^[A-Za-z][A-Za-z0-9_]{2,15}$')  # Nickname must be 3-16 characters, starting with a letter

# Global data structures and locks
clients = {}  # Dictionary of connected clients
channels = {}  # Dictionary of channels and their members
clients_lock = asyncio.Lock()  # Lock for accessing the clients dictionary
channels_lock = asyncio.Lock()  # Lock for accessing the channels dictionary
server_name = "MyIRC"  # Server name for messaging
server_version = "1.0"


class Client:
    """Class representing a connected client."""
    def __init__(self, reader, writer, address):
        self.reader = reader    # StreamReader object for the client
        self.writer = writer    # StreamWriter object for the client
        self.address = address  # IP address and port of the connected client.
        self.nickname = None    # Nickname of the client, will be set after registration.
        self.username = None    # Username provided by the client during registration.
        self.realname = None    # Real name or full name of the client, also set during registration.
        self.last_pong = time.time()  # Last time a PONG was received from the client
        self.channels = set()  # Set of channels the client is a member of
        self.lock = asyncio.Lock()  # Lock for thread-safe operations on this client
        self.registered = False  # Flag to indicate if the client has completed registration
        self.last_activity = time.time()  # Last time the client sent a message
        self.signon_time = time.time()  # Time when the client connected
        self.idle = False  # Flag to indicate if the client is idle
        self.tasks = set()  # Set of tasks for the client

    async def send(self, message):
        """Send a message to the client.

        This function ensures the client receives server messages (including responses to their commands).
        The lock ensures thread-safety since multiple threads could interact with the same client simultaneously.
        """
        try:
            async with self.lock:
                self.writer.write(message.encode('utf-8'))
                await self.writer.drain()
                # self.last_activity = time.time() # Update the last activity timestamp to monitor for idle clients.
        except Exception as e:
            # Log any issue that might occur when sending the message to the client for debugging and monitoring.
            print(f"Error sending message to {self.nickname}: {e}")

    async def close(self, reason="Disconnected"):
        """Close the client's connection and clean up references.

        This method ensures that clients who leave are removed from the server's data structures to avoid memory leaks.
        It also broadcasts a notice to other users to maintain an active conversation flow.
        """
        try:
            self.writer.close() # Close the client's socket to terminate the connection.
            await self.writer.wait_closed()
            self.last_activity = time.time()  # Mark the time the client left.
        except Exception as e:
            print(f"Error closing connection for {self.nickname}: {e}")

        # Cancel all associated tasks
        for task in self.tasks:
            task.cancel()
        self.tasks.clear()

        if self.nickname:
            async with clients_lock:
                if self.nickname in clients:
                    del clients[self.nickname]  # Ensure the client is removed from the global client list.
            await leave_all_channels(self)  # Remove the client from any channels they were part of.
            # Inform all clients in the server that this user has left.
            await broadcast(f":server NOTICE * :{self.nickname} has left the chat room ({reason})\r\n", exclude=self)
            print(f"{self.nickname} has disconnected: {reason}")


async def broadcast(message, exclude=None):
    """Send a message to all clients except one.

    Broadcasting ensures that all users in the chat are informed about general notices, such as users joining or leaving.
    The optional exclude parameter allows certain users (e.g., the one who sent the message) to be excluded from receiving the broadcast.
    """
    async with clients_lock:
        for client in clients.values():
            if client != exclude:
                await client.send(message)  # Notify all clients except the one specified.


async def leave_all_channels(client):
    """Remove a client from all channels they are part of and notify the rest of the channel members.

    This method ensures that when a client leaves, channels are updated appropriately, including removing empty channels.
    Broadcasting the departure keeps users aware of changes in channel membership.
    """
    async with channels_lock:
        for channel in list(client.channels):
            if channel in channels:
                channels[channel].discard(client.nickname)  # Remove the client from the channel's member list.
                # If no users are left in the channel, delete the channel.
                if not channels[channel]:
                    del channels[channel]
                else:
                    # Notify the remaining users in the channel that this client has left.
                    await broadcast(f":{client.nickname}!{client.username}@{client.address[0]} PART {channel}\r\n", exclude=client)
                    await broadcast(f":server NOTICE {channel} :{client.nickname} has left the channel\r\n", exclude=client)
            client.channels.discard(channel)  # Remove the channel from the client's list of joined channels.


def validate_nickname(nickname):
    """Ensure that a nickname meets the required pattern for IRC.

    This helps enforce a consistent naming convention and prevents clients from choosing inappropriate or conflicting names.
    """
    return NICKNAME_REGEX.match(nickname) is not None


async def handle_client(reader, writer):
    """Manage the communication with a connected client.

    This function encapsulates the lifecycle of a client connection, from initial connection, to sending/receiving messages, and finally, disconnection.
    It also starts the PING thread, which ensures the client remains active, sending periodic health checks.
    """
    addr = writer.get_extra_info('peername')
    client = Client(reader, writer, addr)

    # Server allows and remembers a new client connection
    print(f"Client connected: {addr}")

    # Start PING coroutine
    ping_task = asyncio.create_task(ping_client(client))
    client.tasks.add(ping_task)

    # Start IDLE coroutine
    idle_task = asyncio.create_task(detect_idle(client))
    client.tasks.add(idle_task)

    # Main loop for receiving data from the client.
    try:
        while True:
            try:
                data = await reader.readline()
                if not data:
                    print(f"No data received. Closing connection for {client.nickname}")
                    break
                messages = data.decode('utf-8').strip().split('\r\n')
                for message in messages:
                    if message:
                        await process_command(client, message)  # Delegate each message to the appropriate command handler.
                        client.last_activity = time.time()
            except asyncio.TimeoutError:
                print(f"Client {client.nickname} timed out due to inactivity.")  # Log a timeout error.
                break
    except Exception as e:
        print(f"Error receiving data from {client.nickname}: {e}")
    finally:
        await client.close()


async def process_command(client, message):
    """Process IRC commands sent by the client.

    Each message received from the client follows the IRC protocol and is parsed here.
    Based on the command, the appropriate function is called to handle it, ensuring smooth communication between the client and server.
    """
    print(f"Received from {client.nickname or 'Unknown'}: {message}")
    parts = message.split(' ')
    command = parts[0].upper()
    print(f"Command: {command}")
    
    if not client.registered and command not in ['NICK', 'USER', 'QUIT', 'PING', 'PONG']:
        await client.send(f":{server_name} 451 * :You have not registered\r\n")
        return

    # Handle the command based on the IRC protocol
    if command == 'CAP':
        await handle_cap_command(client, parts)

    elif command == "NICK":
        await handle_nick_command(client, parts)

    elif command == "USER":
        await handle_user_command(client, parts)

    elif command == "PONG":
        client.last_pong = time.time()
        print(f"Received PONG from {client.nickname}")

    elif command == "LIST":
        await handle_list_command(client)

    elif command == "JOIN":
        if len(parts) < 2:
            await client.send(f":{server_name} 461 {client.nickname} JOIN :Not enough parameters\r\n")
            return
        channel_name = parts[1]
        if not channel_name.startswith("#"):
            await client.send(f":{server_name} 476 {client.nickname} {channel_name} :Bad channel mask\r\n")
            return
        await join_channel(client, channel_name)

    elif command == "PART":
        if len(parts) < 2:
            await client.send(f":{server_name} 461 {client.nickname} PART :Not enough parameters\r\n")
            return
        channel_name = parts[1]
        await part_channel(client, channel_name)

    elif command == "PRIVMSG":
        if len(parts) < 3:
            await client.send(f":{server_name} 461 {client.nickname} PRIVMSG :Not enough parameters\r\n")
            return
        target, msg = parts[1], ' '.join(parts[2:]).lstrip(':')
        if target.startswith("#"):
            await send_channel_message(client, target, msg)
        else:
            await send_private_message(client, target, msg)

    elif command == "NAMES":
        await handle_names_command(client, parts)

    elif command == "QUIT":
        reason = parts[1].lstrip(':') if len(parts) > 1 else "Client Quit"
        await client.send(f":{server_name} QUIT :{client.nickname} has quit ({reason})\r\n")
        # await leave_all_channels(client)
        await client.close(reason)

    elif command == "WHOIS":
        if len(parts) < 2:
            await client.send(f":{server_name} 431 {client.nickname} :No nickname given\r\n")
        else:
            await handle_whois_command(client, parts[1:])

    elif command == "PING":
        await client.send(f"PONG {parts[1]}\r\n")

    else:
        await client.send(f":{server_name} 421 {client.nickname} {command} :Unknown command\r\n")


async def handle_cap_command(client, parts):
    """Handle the CAP command, which manages capability negotiation between the client and server.

    CAP negotiation is part of the modern IRC protocol to handle features like SASL authentication and multi-prefixes.
    Clients initiate this command to request certain capabilities from the server.
    """
    if len(parts) < 2:
        return

    subcommand = parts[1].upper()
    if subcommand == "LS":
        # List the server-supported capabilities
        capabilities = "multi-prefix sasl"
        await client.send(f":{server_name} CAP {client.nickname} LS :{capabilities}\r\n")
    elif subcommand == "REQ":
        # Client requests to enable certain capabilities
        requested_caps = parts[2].split()
        # Reject all requested capabilities by sending a NAK response
        rejected_caps = " ".join(requested_caps)
        await client.send(f":{server_name} CAP {client.nickname} NAK :{rejected_caps}\r\n")
    elif subcommand == "END":
        # End CAP negotiation
        await client.send(f":{server_name} CAP {client.nickname} END\r\n")
    else:
        # Unknown CAP subcommand
        await client.send(f":{server_name} 410 {client.nickname} :Invalid CAP subcommand\r\n")

async def handle_nick_command(client, parts):
    """Handles the NICK command, which sets or changes the client's nickname.

    Ensuring unique and valid nicknames avoids conflicts and maintains a clear identity for each user.
    """
    if len(parts) < 2:
        await client.send(f":{server_name} 431 * :No nickname given\r\n")
        return
    new_nick = parts[1]
    if not validate_nickname(new_nick):
        await client.send(f":{server_name} 432 * {new_nick} :Erroneous nickname\r\n")
        return

    async with clients_lock:
        if new_nick in clients:
            await client.send(f":{server_name} 433 * {new_nick} :Nickname is already in use\r\n")
            return
        old_nick = client.nickname
        client.nickname = new_nick
        clients[new_nick] = client
        if old_nick and old_nick in clients:
            del clients[old_nick]  # Remove the old nickname reference from the clients dictionary.

    await client.send(f":{server_name} 001 {new_nick} :Nickname set to {new_nick}\r\n")
    await client.send(f":{server_name} 002 {new_nick} :Please send USER command to complete registration\r\n")
    print(f"Client set nickname to {new_nick}")

    # If client already has USER info, complete registration process
    if client.username:
        await complete_registration(client)

async def handle_user_command(client, parts):
    """Handles the USER command, which sets the client's username and realname.

    Completing the USER and NICK commands is required for the client to register and participate fully.
    """
    if len(parts) < 2:
        await client.send(f":{server_name} 461 {client.nickname} USER :Not enough parameters\r\n")
        return
    client.username = parts[1]
    client.realname = ' '.join(parts[4:]).lstrip(':')
    print(f"Client {client.nickname} set username to {client.username}")

    if client.nickname and client.username and not client.registered:
        await complete_registration(client)


async def complete_registration(client):
    """Complete the registration process once both NICK and USER are set and send a welcome message to the client once they have successfully registered.

    This series of messages follows the IRC protocol's welcome sequence, providing
    the client with basic server information, including the number of users.
    """
    client.registered = True  # Mark the client as registered once they provide both NICK and USER details.
    await client.send(f":{server_name} 001 {client.nickname} :Welcome to the IRC network, {client.nickname}\r\n")
    await client.send(f":{server_name} 002 {client.nickname} :Your host is {server_name}, running version {server_version}\r\n")
    await client.send(f":{server_name} 003 {client.nickname} :This server was created at some time\r\n")
    await client.send(f":{server_name} 004 {client.nickname} {server_name} {server_version} o o\r\n")
    # Provide information about the current number of connected users.
    await client.send(f":{server_name} 251 {client.nickname} :There are {len(clients)} users and 1 server\r\n")
    # Broadcast to all clients that a new user has joined.
    await broadcast(f":server NOTICE * :{client.nickname} has joined the chat room\r\n", exclude=client)

async def join_channel(client, channel_name):
    """ To handle the operation of joining the object channel after "JOIN" is received.
    Add the client to a channel and notify other members."""
    async with channels_lock:
        if channel_name not in channels:
            channels[channel_name] = set()
        channels[channel_name].add(client.nickname)
    client.channels.add(channel_name)

    # Send JOIN confirmation message
    await client.send(f":{client.nickname}!{client.username}@{client.address[0]} JOIN {channel_name}\r\n")

    # Send channel topic (if any)
    topic = "No topic is set"  # Placeholder for channel topic
    await client.send(f":{server_name} 332 {client.nickname} {channel_name} :{topic}\r\n")

    # Send NAMES list
    async with channels_lock:
        user_list = ' '.join(channels[channel_name])
    await client.send(f":{server_name} 353 {client.nickname} = {channel_name} :{user_list}\r\n")
    await client.send(f":{server_name} 366 {client.nickname} {channel_name} :End of /NAMES list.\r\n")

    # Notify other members in the channel
    await broadcast(f":{client.nickname}!{client.username}@{client.address[0]} JOIN {channel_name}\r\n", exclude=client)
    print(f"{client.nickname} joined channel {channel_name}")

    # Print the clients in the current channel
    print(f"Current channel {channel_name}: {channels[channel_name]}")


async def handle_names_command(client, parts):
    """To handle the operation of sending each name of the current channel's users after "NAMES" is received.
    Send message of the user's name list in the chatroom, including users in specific channel."""
    if len(parts) < 2:
        # No channel specified, return all user lists
        async with channels_lock:
            for channel in channels:
                user_list = ' '.join(channels[channel])
                await client.send(f":{server_name} 353 {client.nickname} = {channel} :{user_list}\r\n")
        await client.send(f":{server_name} 366 {client.nickname} * :End of /NAMES list.\r\n")
    else:
        channel = parts[1]
        async with channels_lock:
            if channel in channels:
                user_list = ' '.join(channels[channel])
                await client.send(f":{server_name} 353 {client.nickname} = {channel} :{user_list}\r\n")
                await client.send(f":{server_name} 366 {client.nickname} {channel} :End of /NAMES list.\r\n")
            else:
                await client.send(f":{server_name} 403 {client.nickname} {channel} :No such channel\r\n")

async def handle_list_command(client):
    """Handle the LIST command, which lists all channels and their topics."""
    async with channels_lock:
        if not channels:
            await client.send(f":{server_name} 323 {client.nickname} :No channels available\r\n")
            return

        await client.send(f":{server_name} 321 {client.nickname} Channel :Users Name\r\n")
        for channel_name, members in channels.items():
            topic = "No topic set"  # Placeholder for channel topic
            await client.send(f":{server_name} 322 {client.nickname} {channel_name} {len(members)} :{topic}\r\n")
        await client.send(f":{server_name} 323 {client.nickname} :End of /LIST\r\n")

async def part_channel(client, channel_name):
    """To handle the operation of leaving the object channel after "PART" is received.
    Remove the client from a channel and notify other members."""
    async with channels_lock:
        if channel_name in channels and client.nickname in channels[channel_name]:
            # Notify other members in the channel
            await broadcast(f":{client.nickname}!{client.username}@{client.address[0]} PART {channel_name}\r\n", exclude=client)

            # Remove the client from the channel
            channels[channel_name].discard(client.nickname)
            if not channels[channel_name]:
                del channels[channel_name]
            client.channels.discard(channel_name)

            # Send PART confirmation message to the client
            await client.send(f":{client.nickname}!{client.username}@{client.address[0]} PART {channel_name}\r\n")
            print(f"{client.nickname} left channel {channel_name}")
        else:
            await client.send(f":{server_name} 442 {client.nickname} {channel_name} :You're not on that channel\r\n")


async def send_channel_message(sender, channel_name, message):
    """To handle the operation of sending message to the object channel after "PRIVMSG" is received and the second argument start with "#".
    Send a message to all members of a channel."""
    async with channels_lock:
        if channel_name not in channels:
            await sender.send(f":{server_name} 403 {sender.nickname} {channel_name} :No such channel\r\n")
            return
        if sender.nickname not in channels[channel_name]:
            await sender.send(f":{server_name} 442 {sender.nickname} {channel_name} :You're not on that channel\r\n")
            return
        members = channels[channel_name].copy()

    async with clients_lock:
        for member_nick in members:
            if member_nick == sender.nickname:
                continue
            target_client = clients.get(member_nick)
            if target_client:
                try:
                    await target_client.send(f":{sender.nickname}!{sender.username}@{sender.address[0]} PRIVMSG {channel_name} :{message}\r\n")
                except Exception as e:
                    print(f"Error sending channel message to {member_nick}: {e}")
    print(f"{sender.nickname} sent message to {channel_name}: {message}")


async def send_private_message(sender, target_nick, message):
    """To handle the operation of sending private message to the object client after "PRIVMSG" is received.
    Send a private message to a specific client."""
    async with clients_lock:
        target_client = clients.get(target_nick)
    if target_client:
        try:
            await target_client.send(f":{sender.nickname}!{sender.username}@{sender.address[0]} PRIVMSG {target_nick} :{message}\r\n")
            # await sender.send(f":{sender.nickname}!{sender.username}@{sender.address[0]} PRIVMSG {target_nick} :{message}\r\n")
            print(f"{sender.nickname} sent private message to {target_nick}: {message}")
        except Exception as e:
            print(f"Error sending private message to {target_nick}: {e}")
    else:
        await sender.send(f":{server_name} 401 {sender.nickname} {target_nick} :No such nick/channel\r\n")

async def detect_idle(client):
    """Periodically check if the client is idle."""
    while True:
        await asyncio.sleep(RES_TIMEOUT)
        current_time = time.time()
        if current_time - client.last_activity > RES_TIMEOUT:
            print(f"{client.nickname} idle for more than {RES_TIMEOUT} seconds, marking as idle...")
            client.idle = True  # Mark the client as idle
            await client.send(f":{server_name} NOTICE :You have been marked as idle due to inactivity.\r\n")
        else:
            client.idle = False  # Reset idle status if the client is active  

async def ping_client(client):
    """Periodically send PING messages to the client and check for responses in order to insure the connection is maintained."""
    missed_pongs = 0

    while True:
        await asyncio.sleep(PING_INTERVAL)

        try:
            current_time = time.time()

            if current_time - client.last_pong > PING_TIMEOUT:
                missed_pongs += 1
                if missed_pongs >= 3:
                    print(f"{client.nickname} did not respond to PING, disconnecting...")
                    await client.send(f":{server_name} ERROR :Closing Link: {client.nickname} (Ping timeout)\r\n")
                    await client.close("Ping timeout")
                    break
            else:
                missed_pongs = 0
            await client.send("PING :server\r\n")
            print(f"Sent PING to {client.nickname}")
        except Exception as e:
            print(f"Error in ping_client for {client.nickname}: {e}")
            await client.close("Ping thread error")
            break


async def handle_whois_command(client, params):
    """Handle the WHOIS command when 'WHOIS' is received."""
    if len(params) < 1:
        await client.send(f":{server_name} 431 {client.nickname} :No nickname given\r\n")
        return

    target_nick = params[0]
    async with clients_lock:
        target_client = clients.get(target_nick)

    if not target_client:
        await client.send(f":{server_name} 401 {client.nickname} {target_nick} :No such nick/channel\r\n")
        return

    # Send user information
    await client.send(f":{server_name} 311 {client.nickname} {target_client.nickname} {target_client.username} "
                      f"{target_client.address[0]} * :{target_client.realname}\r\n")

    # Send server information
    await client.send(f":{server_name} 312 {client.nickname} {target_client.nickname} {server_name} :Server Info\r\n")

    # Send channel list
    channels_list = ' '.join(target_client.channels)
    await client.send(f":{server_name} 319 {client.nickname} {target_client.nickname} :{channels_list}\r\n")

    # Send idle time and signon time
    idle_time = int(time.time() - target_client.last_activity)
    signon_time = int(target_client.signon_time)
    await client.send(f":{server_name} 317 {client.nickname} {target_client.nickname} {idle_time} {signon_time} "
                      f":seconds idle, signon time\r\n")

    # End of WHOIS
    await client.send(f":{server_name} 318 {client.nickname} {target_client.nickname} :End of /WHOIS list.\r\n")


async def main():
    """Initialize and start the server, accepting and handling client connections."""
    # Create an IPV6 socket to listen for incoming connections
    server_socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((HOST, PORT))
    server_socket.listen(5)
    server_socket.setblocking(False)
    server_socket.settimeout(1.0)

    # Use asyncio to handle the client connection, while using the socket to listen the connection
    server = await asyncio.start_server(handle_client, sock=server_socket)
    addr = server_socket.getsockname()
    print(f"Serving on {addr}")

    async with server:
        await server.serve_forever()


# The main entrance of the server program
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server shut down.")
