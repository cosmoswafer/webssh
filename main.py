import os
from aiohttp import web
from ssh_handler import handle_ssh_connection

routes = web.RouteTableDef()

@routes.get('/')
async def index(request):
    return web.FileResponse('./index.html')

@routes.post('/connect')
async def connect(request):
    data = await request.json()
    return await handle_ssh_connection(request, data)

app = web.Application()
app.add_routes(routes)
app.router.add_static('/static', './static')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    web.run_app(app, port=port)
