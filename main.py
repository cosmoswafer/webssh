import os
import json
import asyncio
from aiohttp import web
from ssh_handler import handle_ssh_connection

routes = web.RouteTableDef()

def sanitize_data_for_logging(data):
    """Sanitize sensitive data for safe logging by masking passwords and private keys."""
    try:
        if isinstance(data, dict):
            sanitized = data.copy()
            # Mask sensitive fields
            if 'password' in sanitized and sanitized['password']:
                sanitized['password'] = '[REDACTED]'
            if 'privateKey' in sanitized and sanitized['privateKey']:
                sanitized['privateKey'] = '[REDACTED]'
            return sanitized
        elif isinstance(data, str):
            try:
                parsed = json.loads(data)
                if isinstance(parsed, dict):
                    return json.dumps(sanitize_data_for_logging(parsed))
            except json.JSONDecodeError:
                # If JSON parsing fails, do not return the original data
                return "[UNSANITIZED DATA REDACTED]"
        # If data is not dict or str, return a safe string
        return "[UNSANITIZED DATA REDACTED]"
    except Exception:
        return "[UNSANITIZED DATA REDACTED]"

@routes.get('/')
async def index(request):
    return web.FileResponse('./index.html')

@routes.get('/connect')
async def connect(request):
    print("Received a connection request")
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    ssh_client = None

    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                    print(f"Received JSON data: {sanitize_data_for_logging(data)}")

                    if not ssh_client:
                        ssh_client = await handle_ssh_connection(ws, data)
                        if isinstance(ssh_client, web.Response):
                            error_message = ssh_client.text
                            await ws.send_str(f"Failed to connect: {error_message}\r\n")
                            break
                        await ws.send_str("Connected to SSH server\r\n")
                    else:
                        if isinstance(data, dict) and 'type' in data and data['type'] == 'resize':
                            cols, rows = data['cols'], data['rows']
                            print(f"Received resize event: {cols}x{rows}")
                            await ssh_client.handle_resize(cols, rows)
                        else:
                            print(f"Received JSON data with unknown type, sending the raw data to SSH server: {sanitize_data_for_logging(data)}")
                            await ssh_client.send_input(msg.data)

                except json.JSONDecodeError:
                    # Handle non-JSON messages
                    print(f"Received non-JSON data: {sanitize_data_for_logging(msg.data)}")
                    if ssh_client:
                        try:
                            await ssh_client.send_input(msg.data)
                        except Exception as e:
                            print(f"Error sending input: {e}")

            elif msg.type == web.WSMsgType.ERROR:
                print(f'WebSocket connection closed with exception {ws.exception()}')
    finally:
        if ssh_client:
            await ssh_client.close()
        print('WebSocket connection closed')

    return ws

app = web.Application()
app.add_routes(routes)
app.router.add_static('/static', './static')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    print(f"Starting server on port {port}")
    print("To run the server, use: uv run main.py")
    web.run_app(app, port=port)
