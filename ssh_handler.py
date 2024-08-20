import asyncio
from ssh_client import SSHClient, SSHClientException
from aiohttp import web

async def handle_ssh_connection(request, data):
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
                    await ws.send_str(output.decode('utf-8'))
                else:
                    await asyncio.sleep(0.1)

        async def receive_input():
            async for msg in ws:
                if msg.type == web.WSMsgType.TEXT:
                    if msg.data.startswith('PASSWORD:'):
                        # Handle password input from client
                        password = msg.data.split(':', 1)[1]
                        ssh_client.password = password
                        try:
                            await ssh_client.connect()
                        except SSHClientException as e:
                            await ws.send_str(f"ERROR: {str(e)}")
                    else:
                        await ssh_client.send_input(msg.data)
                elif msg.type == web.WSMsgType.ERROR:
                    print(f'WebSocket error: {ws.exception()}')

        await asyncio.gather(send_output(), receive_input())

        await ssh_client.close()
        return ws
    except SSHClientException as e:
        if "Enter password" in str(e):
            return web.json_response({'error': 'Password required', 'prompt': str(e)}, status=401)
        return web.json_response({'error': str(e)}, status=400)
    except Exception as e:
        return web.json_response({'error': f"An unexpected error occurred: {str(e)}"}, status=500)
