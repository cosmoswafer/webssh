# Web-Based SSH Terminal

A secure web interface for SSH connections using Python and WebSockets.

## Features

- Web-based terminal interface (Xterm.js integration)
- Secure SSH credential handling
- Real-time terminal synchronization
- Automatic resize propagation
- Query parameter pre-configuration
- Async Python backend using Paramiko

## Quick Start

1. Install requirements:
```bash
pip install -r requirements.txt
```

2. Start server:
```bash
python main.py
```

3. Connect via:
`http://localhost:8080?host=your_server&port=22&username=your_user`

## Configuration

### Environment Variables
Set in `.env` or OS environment:

- `PORT` (default: 8080) - Web server port

### Runtime Options
URL parameters:
- `host` - SSH server hostname (required)
- `port` - SSH port (default: 22)
- `username` - SSH username (required)

## Security Notes

- Passwords are transmitted over WebSocket (ensure HTTPS in production)
- Private keys must be pasted manually in the web interface
- Session credentials are never persisted
- Uses Paramiko's strict security policies

## API Endpoints

- `/` - Main interface (index.html)
- `/connect` - WebSocket endpoint for SSH tunneling
- `/static` - Static assets (JS/CSS)

## Development

```bash
# Run tests
pytest test_ssh_client.py

# Test CLI client directly
python test_ssh_client.py example.com 22 username
```

Follow conventions from [CONVENTIONS.md](CONVENTIONS.md):
- Type-hinted Python code
- Async/await for I/O operations
- WebSocket messages use JSON format:
  ```json
  {"type": "resize", "cols": 80, "rows": 24}
  ```
