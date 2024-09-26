import os
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
                data = msg.json()
                print(f"Request data: {data}")
                
                if not ssh_client:
                    result = await handle_ssh_connection(request, data)
                    if isinstance(result, web.Response):
                        error_message = result.text
                        await ws.send_str(f"Failed to connect: {error_message}\r\n")
                        break
                    else:
                        ssh_client = result
                        await ws.send_str("Connected to SSH server\r\n")
                elif ssh_client:
                    await ssh_client.send_input(data)
                
                if ssh_client:
                    while True:
                        output = await ssh_client.read_output()
                        if not output:
                            break
                        await ws.send_str(output)
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
