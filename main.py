import asyncio
from aiohttp import web
from ssh_client import SSHClient

routes = web.RouteTableDef()

@routes.get('/')
async def index(request):
    return web.FileResponse('./index.html')

@routes.post('/connect')
async def connect(request):
    data = await request.json()
    host = data['host']
    port = int(data['port'])
    username = data['username']
    password = data['password']

    ssh_client = SSHClient(host, port, username, password)
    await ssh_client.connect()
    
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    async def send_output():
        while True:
            output = await ssh_client.read_output()
            if output:
                await ws.send_str(output)
            else:
                break

    async def receive_input():
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                await ssh_client.send_input(msg.data)
            elif msg.type == web.WSMsgType.ERROR:
                print(f'WebSocket error: {ws.exception()}')

    await asyncio.gather(send_output(), receive_input())

    await ssh_client.close()
    return ws

app = web.Application()
app.add_routes(routes)
app.router.add_static('/static', './static')

if __name__ == '__main__':
    web.run_app(app)
