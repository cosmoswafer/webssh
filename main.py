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

    async for msg in ws:
        if msg.type == web.WSMsgType.TEXT:
            data = msg.json()
            print(f"Request data: {data}")
            response = await handle_ssh_connection(request, data)
            await ws.send_str(response)
            print("SSH connection handled")
        elif msg.type == web.WSMsgType.ERROR:
            print(f'WebSocket connection closed with exception {ws.exception()}')

    print('WebSocket connection closed')
    return ws

app = web.Application()
app.add_routes(routes)
app.router.add_static('/static', './static')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    web.run_app(app, port=port)
