# Web-Based SSH Terminal

A secure web interface for SSH connections using Python and WebSockets.

## Features

- Web-based terminal interface (Xterm.js integration)
- Solarized color theme support (dark and light variants)
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

## Terminal Themes

The terminal features Solarized color theme support with multiple theme selection options.

### Theme Selection Priority
1. **Query Parameter**: `?theme=light`, `?theme=dark`, or `?theme=auto` (overrides default)
2. **Default**: Solarized dark theme (when no theme parameter is specified)

### Usage Examples

**URL with theme parameter:**
```
http://localhost:8080?host=server&username=user&theme=light
http://localhost:8080?host=server&username=user&theme=dark
http://localhost:8080?host=server&username=user&theme=auto
```

**Manual theme switching via browser console:**
```javascript
// Switch to solarized dark theme
switchSolarizedTheme(true)

// Switch to solarized light theme  
switchSolarizedTheme(false)
```

**Theme Options:**
- `?theme=light` - Force solarized light theme
- `?theme=dark` - Force solarized dark theme  
- `?theme=auto` - Auto-detect browser's `prefers-color-scheme` setting
- No parameter - Default to solarized dark theme

## Configuration

### Environment Variables
Set in `.env` or OS environment:

- `PORT` (default: 8080) - Web server port

### Runtime Options
URL parameters:
- `host` - SSH server hostname (required)
- `port` - SSH port (default: 22)
- `username` - SSH username (required)
- `theme` - Terminal color theme: `light`, `dark`, or `auto` (optional, defaults to dark theme)

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
