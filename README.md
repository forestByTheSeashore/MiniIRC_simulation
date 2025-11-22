# MiniIRC Simulation

一个基于 Python 实现的简单 IRC (Internet Relay Chat) 服务器和客户端系统，遵循 RFC 1459 协议标准。

A simple IRC (Internet Relay Chat) server and client system implemented in Python, following the RFC 1459 protocol standard.

## 项目简介 | Project Overview

本项目实现了一个功能完整的 IRC 聊天系统，包括服务器、客户端和智能机器人。支持多用户实时通信、频道管理、私聊功能等核心 IRC 特性。

This project implements a fully functional IRC chat system, including server, client, and intelligent bot. It supports multi-user real-time communication, channel management, private messaging, and other core IRC features.

## 主要特性 | Key Features

### 服务器 (Server)
- ✅ **双版本实现**: 提供基于线程 (`server.py`) 和异步 (`server_asyncio.py`) 两个版本
- ✅ **用户认证**: 支持 NICK 和 USER 命令进行用户注册
- ✅ **实时通信**: 支持频道消息和私人消息
- ✅ **频道管理**: 动态创建和删除频道，自动清理空频道
- ✅ **心跳检测**: 定期发送 PING 消息确保连接活跃
- ✅ **昵称验证**: 使用正则表达式验证昵称格式
- ✅ **多种命令**: 支持 NICK, USER, JOIN, PART, PRIVMSG, QUIT, WHOIS, LIST, NAMES, WHO, MODE 等命令
- ✅ **空闲检测**: 自动检测并标记不活跃用户

### 客户端 (Client)
- 💬 **IPv6 支持**: 使用 IPv6 协议连接服务器
- 💬 **频道操作**: 支持加入/离开频道，发送消息
- 💬 **私聊功能**: 支持与其他用户进行私人对话
- 💬 **自动心跳**: 自动响应服务器的 PING 消息

### 智能机器人 (Bot)
- 🤖 **命令响应**:
  - `!hello` - 向用户打招呼
  - `!slap [username]` - 随机或指定拍打用户
  - `!whois <username>` - 查询用户详细信息
  - `!list` - 列出所有活跃频道
- 🤖 **随机回复**: 私聊时从预设列表中随机回复
- 🤖 **用户列表**: 自动获取频道用户列表
- 🤖 **心跳机制**: 定期发送 PING 保持连接

## 项目结构 | Project Structure

```
MiniIRC_simulation/
├── server.py           # 基于线程的 IRC 服务器实现 | Thread-based IRC server implementation
├── server_asyncio.py   # 基于 asyncio 的异步 IRC 服务器实现 | Async IRC server implementation with asyncio
├── client.py           # IRC 客户端实现（包含普通客户端和机器人客户端）| IRC client implementation (includes regular client and bot client)
├── bot.py              # 独立的智能机器人实现 | Standalone intelligent bot implementation
└── facts.txt           # 机器人回复使用的随机事实列表 | Random facts list for bot responses
```

## 安装要求 | Requirements

- Python 3.7+
- 标准库依赖 | Standard library dependencies: `socket`, `threading`, `asyncio`, `re`, `argparse`, `time`
- 外部依赖 | External dependencies: `psutil` (仅异步服务器需要 | only required for async server)

安装外部依赖（使用异步服务器时） | Install external dependencies (when using async server):
```bash
pip install psutil
```

**注意** | **Note**: 
- 使用 `server.py` (线程版本) 不需要安装 psutil | Using `server.py` (threaded version) does not require psutil
- 使用 `server_asyncio.py` (异步版本) 需要安装 psutil | Using `server_asyncio.py` (async version) requires psutil

## 快速开始 | Quick Start

### 1. 启动服务器 | Start Server

**选项 A: 使用线程版本 | Using Thread-based Version**
```bash
python server.py
```

**选项 B: 使用异步版本 | Using Async Version**
```bash
python server_asyncio.py
```

服务器将在 `[::]:6667` 端口监听连接。

The server will listen on `[::]:6667` for connections.

### 2. 连接客户端 | Connect Client

您可以使用任何 IRC 客户端（如 HexChat）或本项目提供的客户端连接服务器。

You can use any IRC client (e.g., HexChat) or the provided client to connect to the server.

**使用项目客户端 | Using Project Client**
```bash
python client.py --host <server_address> --port 6667 --name <nickname> --channel <channel_name>
```

例如 | Example:
```bash
python client.py --host "::1" --port 6667 --name Alice --channel "#general"
```

### 3. 启动机器人 | Start Bot

```bash
python bot.py --host <server_address> --port 6667 --name SuperBot --channel <channel_name>
```

例如 | Example:
```bash
python bot.py --host "::1" --port 6667 --name SuperBot --channel "#hello"
```

**注意**: 频道名不需要包含 `#` 符号，程序会自动添加。

**Note**: The channel name does not need to include the `#` symbol; the program will add it automatically.

## 使用指南 | Usage Guide

### 基本命令 | Basic Commands

连接服务器后，您可以使用以下命令：

After connecting to the server, you can use the following commands:

- `/nick <new_nickname>` - 更改昵称 | Change nickname
- `/join #<channel_name>` - 加入频道 | Join a channel
- `/part #<channel_name>` - 离开频道 | Leave a channel
- `/msg #<channel_name> <message>` - 向频道发送消息 | Send message to channel
- `/msg <nickname> <message>` - 向用户发送私信 | Send private message to user
- `/quit [reason]` - 断开连接 | Disconnect
- `/whois <nickname>` - 查询用户信息 | Query user information
- `/list` - 列出所有频道 | List all channels
- `/names [#<channel_name>]` - 列出频道成员 | List channel members

### 机器人命令 | Bot Commands

在频道中使用以下命令与机器人互动：

Use the following commands to interact with the bot in a channel:

- `!hello` - 机器人会向你打招呼 | Bot will greet you
- `!slap` - 机器人会随机拍打频道中的一个用户 | Bot will randomly slap a user in the channel
- `!slap <username>` - 机器人会拍打指定用户 | Bot will slap the specified user
- `!whois <username>` - 查询用户的详细信息 | Query detailed information about a user
- `!list` - 列出所有活跃的频道信息 | List all active channel information

### HexChat 客户端测试 | Testing with HexChat

1. 打开 HexChat 客户端 | Open HexChat client
2. 添加新的网络，服务器地址格式: `[IPv6地址]:6667` | Add a new network with server address format: `[IPv6_address]:6667`
3. 设置昵称和用户名 | Set nickname and username
4. 连接到服务器 | Connect to the server
5. 使用 `/join #频道名` 加入频道 | Use `/join #channel_name` to join a channel
6. 开始聊天！| Start chatting!

## 技术实现 | Technical Implementation

### 服务器实现 | Server Implementation

- **server.py**: 使用 Python `threading` 模块实现多线程服务器，每个客户端连接由独立线程处理
  
  Uses Python `threading` module to implement a multi-threaded server, where each client connection is handled by an independent thread

- **server_asyncio.py**: 使用 Python `asyncio` 模块实现异步服务器，能够高效处理大量并发连接
  
  Uses Python `asyncio` module to implement an asynchronous server, capable of efficiently handling a large number of concurrent connections

### 网络协议 | Network Protocol

- 使用 TCP/IPv6 协议进行通信 | Uses TCP/IPv6 protocol for communication
- 默认端口: 6667 (标准 IRC 端口) | Default port: 6667 (standard IRC port)
- 消息格式遵循 IRC 协议标准 (RFC 1459) | Message format follows IRC protocol standard (RFC 1459)

### 心跳机制 | Heartbeat Mechanism

- 服务器每 60 秒发送 PING 消息 | Server sends PING messages every 60 seconds
- 客户端必须在 120 秒内响应 PONG | Client must respond with PONG within 120 seconds
- 未响应的客户端将被自动断开连接 | Unresponsive clients will be automatically disconnected

## 已知问题 | Known Issues

1. ⚠️ 不支持 SSL/TLS 加密，通信为明文传输 | Does not support SSL/TLS encryption; communication is in plaintext
2. ⚠️ 未完全实现所有 IRC 协议规范 | Does not fully implement all IRC protocol specifications
3. ⚠️ 某些高级功能可能需要进一步完善 | Some advanced features may need further refinement

## 未来改进 | Future Improvements

1. 🔧 添加 SSL/TLS 支持以加密通信 | Add SSL/TLS support for encrypted communication
2. 🔧 实现更多 IRC 命令和功能 | Implement more IRC commands and features
3. 🔧 添加用户认证机制 | Add user authentication mechanism
4. 🔧 集成第三方大语言模型 API 用于智能回复 | Integrate third-party large language model APIs for intelligent responses
5. 🔧 改进错误处理和日志记录 | Improve error handling and logging

## 作者 | Authors

- Hongyu Lin
- Jingran Li
- Siming Lv
- Chengyang Zhu
- Zijian Zhou

## 开发日期 | Development Date

- 初始版本: 2024/09/20
- 异步版本: 2024/10/04

## 许可证 | License

本项目为教育目的开发，供学习和研究使用。

This project is developed for educational purposes, for learning and research use.

## 联系方式 | Contact

如有问题或建议，请在 GitHub 上提交 Issue。

For questions or suggestions, please submit an issue on GitHub.

---

**注意**: 本项目仅供学习和测试使用，不建议在生产环境中部署。

**Note**: This project is for learning and testing purposes only. It is not recommended for production deployment.
