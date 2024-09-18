import socket
import random
import argparse
import threading


class Client:
    def __init__(self, host, port, name, channel):
        self.server = host
        self.port = port
        self.name = name
        self.channel = channel
        self.socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        self.socket.settimeout(300)
        self.running = True  # 用于控制接收消息线程的运行

    # 连接到服务器并加入频道
    def connect(self):
        print(f"连接到服务器 {self.server}...")
        self.socket.connect((self.server, self.port, 0, 0))
        self.send_command(f"NICK {self.name}")
        self.send_command(f"USER {self.name} 0 * :{self.name}")
        self.join_channel(self.channel)

    # 发送指令到 IRC 服务器
    def send_command(self, command):
        print(f"发送: {command}")
        self.socket.send((command + "\r\n").encode())

    # 加入频道
    def join_channel(self, channel):
        self.send_command(f"JOIN {channel}")

    # 发送消息到频道
    def send_message(self, channel, message):
        self.send_command(f"PRIVMSG {channel} :{message}")

    # 处理接收到的消息
    def handle_message(self, message):
        print(f"收到消息: {message}")
        if message.startswith("PING"):
            self.send_command(f"PONG {message.split()[1]}")  # 回应服务器的 PING
        elif "PRIVMSG" in message:
            user = message.split("!")[0][1:]  # 获取用户名
            channel = message.split()[2]
            msg_content = message.split(f"PRIVMSG {channel} :")[1]
            print(f"{user}@{channel}: {msg_content}")

    # 主循环，持续接收并处理消息
    def run(self):
        while self.running:
            try:
                response = self.socket.recv(2048).decode("utf-8")
                if response:
                    for line in response.strip().split("\r\n"):
                        self.handle_message(line)
            except socket.timeout:
                print("连接超时。")
                break
            except Exception as e:
                if self.running:  # 只在非正常停止时打印错误
                    print(f"发生错误: {e}")
                break
        print("接收消息线程已停止。")

    # 停止客户端
    def stop(self):
        self.running = False
        self.socket.close()


# 定义机器人的命令响应功能
class IRCBot:

    def __init__(self, host, port, name, channel):
        self.server = host
        self.port = port
        self.name = name
        self.channel = channel
        self.socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
        self.socket.settimeout(300)
        self.responses = [
            "有趣的事实：猫头鹰的眼睛并不能移动！",
            "无聊的事实：你刚才浪费了2秒时间！",
            "随机的回答！",
        ]

    # 连接到服务器并加入频道
    def connect(self):
        print(f"连接到服务器 {self.server}...")
        self.socket.connect((self.server, self.port, 0, 0))
        self.send_command(f"NICK {self.name}")
        self.send_command(f"USER {self.name} 0 * :{self.name}")
        self.join_channel(self.channel)

    # 发送指令到IRC服务器
    def send_command(self, command):
        print(f"发送: {command}")
        self.socket.send((command + "\r\n").encode())

    # 加入频道
    def join_channel(self, channel):
        self.send_command(f"JOIN {channel}")

    # 处理接收到的消息
    def handle_message(self, message):
        print(f"收到消息: {message}")
        if message.startswith("PING"):
            self.send_command(f"PONG {message.split()[1]}")  # 回应服务器的PING

        elif "PRIVMSG" in message:
            user = message.split("!")[0][1:]  # 获取用户名
            channel = message.split()[2]
            msg_content = message.split(f"PRIVMSG {channel} :")[1]

            if msg_content.startswith("!"):
                self.process_command(user, channel, msg_content.strip())

            else:
                # 私信随机回复
                if channel == self.name:  # 如果频道名等于机器人的名字，则是私信
                    random_reply = random.choice(self.responses)
                    self.send_command(f"PRIVMSG {user} :{random_reply}")

    # 处理特定命令
    def process_command(self, user, channel, command):
        if command == "!hello":
            self.send_command(f"PRIVMSG {channel} :Hello {user}!")

        elif command.startswith("!slap"):
            other_users = self.get_other_users(channel, user)
            if other_users:
                target = random.choice(other_users)
                self.send_command(f"PRIVMSG {channel} :{user} 打了 {target} 一巴掌！")
            else:
                self.send_command(f"PRIVMSG {channel} :没有其他用户可供拍打。")

    def get_other_users(self, channel, exclude_user):
        self.send_command(f"NAMES {channel}")
        response = self.socket.recv(2048).decode("utf-8")
        # 根据响应提取用户列表（简单示例，需根据具体的IRC服务器响应格式处理）
        user_list = [
            user
            for user in response.split()
            if user != exclude_user and user != self.name
        ]
        return user_list

    # 主循环，持续接收并处理消息
    def run(self):
        while True:
            try:
                response = self.socket.recv(2048).decode("utf-8")
                if response:
                    for line in response.strip().split("\r\n"):
                        self.handle_message(line)
            except socket.timeout:
                print("连接超时。")
                break
            except Exception as e:
                print(f"发生错误: {e}")
                break


# 使用 argparse 解析命令行参数
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IRC Client")
    parser.add_argument("--role", type=str, default="user", help="Client Type")
    parser.add_argument(
        "--host", type=str, default="fc00:1337::17", help="Server address"
    )
    parser.add_argument("--port", type=int, default=6666, help="Server Port")
    parser.add_argument("--name", type=str, default="SuperBot", help="Nickname")
    parser.add_argument("--channel", type=str, default="#hello", help="Channel to join")

    args = parser.parse_args()

    if args.role == "robot":
        bot = IRCBot(args.host, args.port, args.name, args.channel)
        bot.connect()
        bot.run()
    else:
        user = Client(args.host, args.port, args.name, args.channel)
        user.connect()

        # 运行接收消息的线程
        receive_thread = threading.Thread(target=user.run)
        receive_thread.start()

        # 发送消息
        try:
            while True:
                receive_thread.wait()
                msg = input("输入消息 ('/quit' 退出): ")
                if msg == "/quit":
                    user.stop()  # 停止接收消息线程
                    receive_thread.join()  # 等待接收消息线程结束
                    print("已退出客户端。")
                    break
                user.send_message(args.channel, msg)
        except KeyboardInterrupt:
            user.stop()
            receive_thread.join()
            print("\n退出客户端")
            
