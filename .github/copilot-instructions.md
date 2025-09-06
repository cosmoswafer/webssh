# WebSSH - Web-Based SSH Terminal

WebSSH is a Python web application using aiohttp that provides a secure web interface for SSH connections via WebSocket tunneling. The terminal interface uses Xterm.js with Solarized color theme support.

**Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.**

## Working Effectively

### Bootstrap and Setup
- Install Python dependencies:
  - `pip install -r requirements.txt` -- takes ~60-90 seconds for fresh install, ~1 second if cached. NEVER CANCEL.
- Start the web server:
  - `python main.py` -- starts in ~1-2 seconds on port 8080
- Access the web interface:
  - Navigate to `http://localhost:8080`
  - The form will load but may show CDN errors in restricted environments

### Build and Test
- **No formal build process required** - this is a pure Python web application
- **No automated test suite exists** - validation is manual
- Syntax validation:
  - `python -m py_compile main.py ssh_client.py ssh_handler.py test_ssh_client.py`
- CLI test script available (interactive, requires real SSH server):
  - `python test_ssh_client.py <host> <port> <username>` -- requires password input

## Validation

### Critical Manual Validation Steps
After making any changes, **ALWAYS** perform these validation steps:

1. **Dependency installation test:**
   ```bash
   pip install -r requirements.txt
   ```
   Expected time: 60-90 seconds fresh, ~1 second cached. NEVER CANCEL.

2. **Server startup test:**
   ```bash
   python main.py
   ```
   Expected output: "Starting server on port 8080" within 1-2 seconds. NEVER CANCEL.

3. **Web interface test:**
   - Navigate to `http://localhost:8080`
   - Verify the SSH connection form loads with fields: Host, Port (default 22), Username, Authentication Method (Password/Private Key), Password
   - Note: CDN resources may be blocked in sandboxed environments causing JavaScript errors, but the form should still be visible

4. **Python syntax validation:**
   ```bash
   python -m py_compile main.py ssh_client.py ssh_handler.py test_ssh_client.py
   ```
   Expected: No output on success

### End-to-End Testing Scenarios
**Important:** Full SSH functionality testing requires access to an actual SSH server, which may not be available in all environments.

Basic connection flow to test (if SSH server available):
1. Fill in Host, Port, Username in the web form
2. Select Password or Private Key authentication
3. Click Connect button
4. If successful, terminal interface should appear
5. Type commands and verify responses

## Project Structure

### Key Files
- `main.py` - Main web server using aiohttp, handles HTTP routes and WebSocket connections
- `ssh_client.py` - SSH client wrapper using Paramiko for async SSH connections  
- `ssh_handler.py` - WebSocket to SSH bridge handler
- `requirements.txt` - Python dependencies (aiohttp, paramiko, etc.)
- `index.html` - Main web interface with SSH connection form
- `static/js/app.js` - Frontend JavaScript with Xterm.js terminal and Solarized themes
- `test_ssh_client.py` - CLI test script for manual SSH testing

### Important Code Paths
- WebSocket endpoint: `/connect` in `main.py`
- SSH connection handling: `handle_ssh_connection()` in `ssh_handler.py`
- Terminal resize events: `handle_resize()` in `ssh_client.py`
- Theme switching: Solarized light/dark themes in `static/js/app.js`

## Development Environment

### Dependencies
- Python 3.12+ (tested with 3.12.3)
- Required packages: aiohttp, paramiko, asyncio (see requirements.txt for full list)
- Frontend: Xterm.js, Bulma CSS (loaded from CDN)

### Environment Variables
- `PORT` - Web server port (default: 8080)

### URL Parameters
The application supports these query parameters:
- `host` - SSH server hostname (required)
- `port` - SSH port (default: 22)  
- `username` - SSH username (required)
- `theme` - Terminal theme: `light`, `dark`, or `auto` (optional, defaults to dark)

Example: `http://localhost:8080?host=server&port=22&username=user&theme=light`

## Common Tasks

### Repository Root Structure
```
.
├── README.md
├── requirements.txt
├── main.py
├── ssh_client.py
├── ssh_handler.py
├── test_ssh_client.py
├── index.html
├── static/
│   └── js/
│       └── app.js
├── maskfile.md
├── LICENSE.txt
└── .gitignore
```

### Frequently Used Commands
```bash
# Install dependencies
pip install -r requirements.txt

# Start development server
python main.py

# Test syntax
python -m py_compile *.py

# Manual SSH test (requires real server)
python test_ssh_client.py example.com 22 username
```

## Security Notes
- Passwords transmitted over WebSocket (use HTTPS in production)
- Private keys pasted manually in web interface
- Session credentials never persisted
- Uses Paramiko's strict security policies
- Sensitive data automatically sanitized in logs

## Troubleshooting

### Common Issues
1. **CDN Resources Blocked**: External JavaScript libraries may be blocked in restricted environments. The form will still function but terminal features may not work.

2. **Authentication Failures**: Ensure SSH server allows the authentication method being used (password vs key-based).

3. **Connection Timeouts**: WebSocket connections require stable network connectivity between browser and server.

### No Formal Linting
- No linting tools are configured in this repository
- Basic syntax validation available with `python -m py_compile`
- Consider adding flake8 or black if implementing code style standards

## Known Limitations
- No automated test suite exists
- No CI/CD pipelines configured  
- External CDN dependencies may be blocked in restricted environments
- Full functionality testing requires access to real SSH servers