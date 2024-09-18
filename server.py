import socket
import threading
# 信号处理
import signal
import sys

# 创建服务器套接字
server_socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

# 绑定端口6667，并监听所有IPv6地址
server_socket.bind(('::', 6667))
server_socket.listen(5)

print("Server activated, waiting for connection...")

clients = {}
channels = {}

def handle_client(client_socket, addr):
    username = None
    nickname = None
    realname = None
    connected = False

    while not connected:
        try:
            message = client_socket.recv(1024).decode('utf-8').strip()
            lines = message.split('\r\n')
            for line in lines:
                if line.startswith("NICK"):
                    nickname = line.split(" ")[1]
                    print(f"Received NICK: {nickname}")
                elif line.startswith("USER"):
                    parts = line.split(" ")
                    username = parts[1]
                    realname = " ".join(parts[4:])[1:]  # 去掉前面的冒号
                    connected = True
                    clients[nickname] = client_socket
                    client_socket.sendall(f":server 001 {nickname} :Welcome to the IRC server {nickname}\r\n".encode('utf-8'))
                    print(f"{nickname} ({realname}) connected: {addr}")
                    broadcast(f":server NOTICE * :{nickname} has joined the chat room\r\n", client_socket)
        except Exception as e:
            print(f"Error receiving message: {e}")
            break

    while True:
        try:
            message = client_socket.recv(1024).decode('utf-8').strip()
            print(message)

            if not message:
                break

            lines = message.split('\r\n')
            for line in lines:
            # 解析命令
                if line.startswith("JOIN"):
                    # 加入频道命令, 格式: /join #channel_name
                    _, channel_name = line.split(" ", 1)
                    print(f"channel: {channel_name}")
                    join_channel(client_socket, nickname, channel_name)
                    

                elif line.startswith("MSG #"):
                    # 发送频道消息, 格式: /msg #channel_name message
                    _, channel_name, msg = line.split(" ", 2)
                    send_channel_message(channel_name, nickname, msg)

                elif line.startswith("MSG"):
                    # 发送私聊消息, 格式: /msg username message
                    _, target_user, msg = line.split(" ", 2)
                    send_private_message(nickname, target_user, msg)

                else:
                    client_socket.sendall(b"Unknown command. Please use /join, /msg #channel, or /msg username.\n")
        except:
            break

    # 客户端断开连接
    client_socket.close()
    del clients[nickname]
    broadcast(f"{nickname} has left the chat room", client_socket)

def broadcast(message, exclude_socket=None):
    for client_socket in clients.values():
        if client_socket != exclude_socket:
            client_socket.sendall(message.encode('utf-8'))

# channels = {}

def join_channel(client_socket, username, channel_name):
    if channel_name not in channels:
        channels[channel_name] = []

    channels[channel_name].append(username)
    client_socket.sendall(f"You've entered the channel: {channel_name}".encode('utf-8'))
    broadcast(f"{username} joined the channel {channel_name}", exclude_socket=client_socket)

def send_channel_message(channel_name, username, message):
    if channel_name in channels:
        for member in channels[channel_name]:
            if member in clients:
                clients[member].sendall(f"[{channel_name}] {username}: {message}".encode('utf-8'))

def send_private_message(username_from, username_to, message):
    if username_to in clients:
        clients[username_to].sendall(f"Chat from {username_from}: {message}".encode('utf-8'))
    else:
        clients[username_from].sendall(f"{username_to} is offline".encode('utf-8'))

def signal_handler(sig, frame):
    print("Shutting down server...")
    # client_socket.close()
    server_socket.close()
    sys.exit(0)

def start_server():
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    while True:
        client_socket, addr = server_socket.accept()
        print(f"Client connected: {addr}")
        client_handler = threading.Thread(target=handle_client, args=(client_socket, addr))
        client_handler.start()

if __name__ == "__main__":
    start_server()