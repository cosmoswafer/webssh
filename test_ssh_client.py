import asyncio
from ssh_client import SSHClient, SSHClientException
import sys
import argparse

async def handle_ssh_connection(host, port, username, password):
    try:
        ssh_client= SSHClient(host, port, username, password)
        await ssh_client.connect()

        async def send_output():
            while True:
                output = await ssh_client.read_output()
                if output:
                    print(output.decode('utf-8', errors='replace'))
                else:
                    await asyncio.sleep(0.1)

        asyncio.create_task(send_output())

        return ssh_client
    except SSHClientException as e:
        print(e)
        return False

async def read_user_input(ssh_client):
    try:
        while True:
            user_input = input('Enter command: ')
            if user_input.lower() == 'exit':
                break
            else:
                await ssh_client.send_input(user_input + "\n")
            await asyncio.sleep(1)  # Keep the connection open
    finally:
        await ssh_client.close()

async def main():
    parser = argparse.ArgumentParser(description="SSH Client")
    parser.add_argument("host", type=str, help="SSH server hostname")
    parser.add_argument("port", type=int, help="SSH server port")
    parser.add_argument("username", type=str, help="SSH username")
    password = input("Enter SSH password: ")
    args = parser.parse_args()

    ssh_client = await handle_ssh_connection(args.host, args.port, args.username, password)
    if ssh_client:
        await ssh_client.send_input("date\n")
        await asyncio.sleep(1)
        input_task = asyncio.create_task(read_user_input(ssh_client))
        await input_task

if __name__ == "__main__": 
    asyncio.run(main())
