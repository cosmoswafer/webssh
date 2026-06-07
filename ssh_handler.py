import asyncio
from aiohttp import web
from ssh_client import SSHClient, SSHClientException

VALID_SESSION_MODES = {'none', 'screen', 'tmux'}


def normalize_session_mode(data):
    session_mode = data.get('sessionMode')
    if session_mode in VALID_SESSION_MODES:
        return session_mode
    if session_mode is not None:
        raise SSHClientException(f"Unsupported session mode: {session_mode}")

    if data.get('enableScreenSession'):
        return 'screen'

    return 'none'

async def handle_ssh_connection(ws, data):
    host = data['host']
    port = int(data['port'])
    username = data['username']
    password = data.get('password')
    private_key = data.get('privateKey')
    session_mode = normalize_session_mode(data)

    try:
        ssh_client = SSHClient(host, port, username, password, private_key)
        await ssh_client.connect()

        if session_mode != 'none':
            await ssh_client.start_session(session_mode)

        async def send_output():
            while True:
                output = await ssh_client.read_output()
                if output:
                    try:
                        await ws.send_str(output.decode('utf-8', errors='replace'))
                    except Exception as e:
                        print(f"Error sending output: {e}")
                        break
                else:
                    await asyncio.sleep(0.1)

        asyncio.create_task(send_output())
        return ssh_client

    except SSHClientException as e:
        if "Enter password" in str(e):
            return web.Response(text='Password required', status=401)
        return web.Response(text=str(e), status=400)
    except Exception as e:
        return web.Response(text=f"An unexpected error occurred: {str(e)}", status=500)
