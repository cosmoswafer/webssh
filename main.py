import os
import json
import asyncio
from aiohttp import web
from ssh_handler import handle_ssh_connection

routes = web.RouteTableDef()

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
                    print(f"Received JSON data: {data}")

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
                            print(f"Received JSON data with unknown type, sending the raw data to SSH server: {data}")
                            await ssh_client.send_input(msg.data)

                except json.JSONDecodeError:
                    # Handle non-JSON messages
                    print(f"Received non-JSON data: {msg.data}")
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
