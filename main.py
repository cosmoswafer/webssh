import asyncio
import os
from aiohttp import web
from ssh_client import SSHClient, SSHClientException

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
    password = data.get('password')  # Use get() to allow for None if password is not provided

    try:
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
    except SSHClientException as e:
        return web.json_response({'error': str(e)}, status=400)
    except Exception as e:
        return web.json_response({'error': f"An unexpected error occurred: {str(e)}"}, status=500)

app = web.Application()
app.add_routes(routes)
app.router.add_static('/static', './static')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    web.run_app(app, port=port)
