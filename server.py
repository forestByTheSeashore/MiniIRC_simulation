import socket
import threading
# 信号处理
import signal
import sys
import time

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
    last_pong_time = time.time()

    def send_ping():
        while True:
            time.sleep(60)
            try:
                ping_message = "PING :server\r\n"
                client_socket.sendall(ping_message.encode('utf-8'))
                # print(f"Sent: {ping_message.strip()}")
            except Exception as e:
                # print(f"Error sending PING: {e}")
                break

    ping_thread = threading.Thread(target=send_ping)
    ping_thread.start()

    while not connected:
        try:
            # print("Waiting for NICK and USER commands...")
            message = client_socket.recv(1024).decode('utf-8').strip()
            # print(f"message for client: {message}")
            lines = message.split('\r\n')
            for line in lines:
                if line.startswith("NICK"):
                    nickname = line.split(" ")[1]
                    print(f"nickname: {nickname}")

                    if nickname in clients:
                        client_socket.sendall(f"ERROR :Nickname is already in use\r\n".encode('utf-8'))
                        #continue
                        #关闭客户端连接，阻止其继续连接
                        client_socket.close()
                        return  # 直接返回，终止该客户端的处理
                    else:
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
            print(f"message for client: {message}")

            if not message:
                break

            # 解析命令
            lines = message.split('\r\n')
            for line in lines:
                if line.startswith("PONG"):
                    last_pong_time = time.time()
                elif line.startswith("JOIN"):
                    # 加入频道命令, 格式: /join #channel_name
                    _, channel_name = line.split(" ", 1)
                    print(f"channel: {channel_name}")
                    join_channel(client_socket, nickname, channel_name)
                elif line.startswith("PRIVMSG"):
                     # 发送消息命令, 格式: PRIVMSG #channel_name :message 或 PRIVMSG username :message
                    parts = line.split(" ", 2)
                    target = parts[1]
                    msg = parts[2][1:]  # 去掉前面的冒号
                    if target.startswith("#"):
                        send_channel_message(target, nickname, msg)
                    else:
                        send_private_message(nickname, target, msg)
                    # 发送频道消息, 格式: /msg #channel_name message
                    # _, channel_name, msg = line.split(" ", 2)
                    # send_channel_message(channel_name, nickname, msg)
                # elif line.startswith("MSG"):
                #     # 发送私聊消息, 格式: /msg username message
                #     _, target_user, msg = line.split(" ", 2)
                #     send_private_message(nickname, target_user, msg)
                elif line.startswith("QUIT"):
                    # 退出命令, 格式: /quit
                    client_socket.sendall(f"Goodbye, {nickname}!\r\n")
                    break
                else:
                    client_socket.sendall(f"Unknown command. Please use /join, /msg #channel, or /msg username.\r\n")

            if time.time() - last_pong_time > 120:
                print(f"{nickname} did not respond to PING, disconnecting...")
                client_socket.sendall(f"ERROR :Closing Link: {nickname} (Ping timeout)\r\n")
                break
        except:
            break

    # 客户端断开连接
    client_socket.close()
    del clients[nickname]
    broadcast(f"{nickname} has left the chat room\r\n", client_socket)

def broadcast(message, exclude_socket=None):
    # print(f"Broadcasting message: {message.strip()}")
    # print(f"Current clients: {list(clients.keys())}")
    for client_socket in clients.values():
        if client_socket != exclude_socket:
            try:
                client_socket.sendall(message.encode('utf-8'))
                print(f"Broadcasted: {message.strip()}")
            except Exception as e:
                print(f"Error broadcasting message: {e}")

def join_channel(client_socket, username, channel_name):
    if channel_name not in channels:
        channels[channel_name] = []

    channels[channel_name].append(username)
    client_socket.sendall(f"You've entered the channel: {channel_name}\r\n".encode('utf-8'))
    broadcast(f"{username} joined the channel {channel_name}\r\n", exclude_socket=client_socket)

def send_channel_message(channel_name, username, message):
    if channel_name in channels:
        for member in channels[channel_name]:
            if member in clients:
                try:
                    clients[member].sendall(f"[{channel_name}] {username}: {message}\r\n".encode('utf-8'))
                except Exception as e:
                    print(f"Error sending channel message to {member}: {e}")

def send_private_message(username_from, username_to, message):
    if username_to in clients:
        clients[username_to].sendall(f"Chat from {username_from}: {message}\r\n".encode('utf-8'))
    else:
        clients[username_from].sendall(f"{username_to} is offline\r\n".encode('utf-8'))

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