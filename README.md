# Mini IRC Simulation

Python implementation of a lightweight IRC stack for local experimentation. The repo contains two server variants, a simple CLI client, and two bots for scripted interactions.

## Project Layout
- `server.py` – Threaded IPv6 server that handles core IRC flow (`NICK`, `USER`, `JOIN`, `PART`, `PRIVMSG`, `PING`/`PONG`) with heartbeat checks and dynamic channel management.
- `server_asyncio.py` – Asyncio server with broader RFC 1459 coverage (`QUIT`, `LIST`, `NAMES`, `WHO`, `WHOIS`, `MODE`, `CAP`, etc.), idle tracking, and safer concurrency via async locks.
- `client.py` – Minimal CLI client. Runs in interactive user mode or a lightweight bot mode (`--role robot`) that replies to a few commands.
- `bot.py` – Featureful bot that replies to `!hello`, `!slap`, `!list`, `!whois`, and can send random facts or private replies.
- `facts.txt` – Fact snippets used by `bot.py`.

## Requirements
- Python 3.10+.
- `psutil` is required only for `server_asyncio.py`:
  ```bash
  pip install psutil
  ```

## Quick Start (local loopback)
1) (Optional) Create a virtual environment:
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt  # if you add one, otherwise install psutil manually
```

2) Start a server (default host `::`, port `6667`):
```bash
python server_asyncio.py
# or: python server.py
```

3) Start a test client against the server:
```bash
python client.py --host ::1 --port 6667 --name alice --channel #hello
```
- Type messages and press Enter to broadcast to the joined channel.
- Use `/quit` to exit cleanly.
- To try the built-in lightweight bot mode instead: `python client.py --role robot --host ::1 --port 6667 --name miniBot --channel #hello`.

4) Run the richer bot that uses `facts.txt`:
```bash
python bot.py --host ::1 --port 6667 --name SuperBot --channel hello
```
Note: pass the channel without `#`; the script adds it when needed.

## Supported Commands (server highlight)
- `NICK` / `USER` – registration
- `JOIN` / `PART` – channel membership
- `PRIVMSG` – channel or direct messaging
- `PING` / `PONG` – heartbeat handling
- Extras in `server_asyncio.py`: `QUIT`, `LIST`, `NAMES`, `WHO`, `WHOIS`, `MODE`, `CAP`

## Tips
- The code listens on IPv6 by default (`AF_INET6`). Use `::1` for local testing. If your IRC client prefers IPv4, update the socket family in the server/client or use an IPv6-capable client.
- Align client port flags with the server port (both servers default to `6667`; `client.py` defaults to `6666`, so override with `--port 6667`).
- No TLS is implemented; traffic is plain TCP.

## Known Limitations
- Not a full RFC-compliant implementation; edge cases and additional numerics are still missing.
- No SSL/TLS support.
- IPv6-only sockets by default; adjust if your environment needs IPv4.
