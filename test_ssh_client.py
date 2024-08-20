import asyncio
from ssh_client import SSHClient, SSHClientException

async def test_ssh_client(host, port, username, password):
    try:
        # Create an SSHClient instance
        ssh_client = SSHClient(host, port, username, password)

        # Connect to the SSH server
        print("Connecting to SSH server...")
        await ssh_client.connect()
        print("Connected successfully!")

        # Send a command
        command = "ls -la"
        print(f"Sending command: {command}")
        await ssh_client.send_input(command + "\n")

        # Read the output
        print("Reading output:")
        while True:
            output = await ssh_client.read_output()
            if output:
                print(output.decode('utf-8'), end='')
            else:
                await asyncio.sleep(0.1)
                break

        # Close the connection
        print("\nClosing connection...")
        await ssh_client.close()
        print("Connection closed.")

    except SSHClientException as e:
        print(f"SSH Client Exception: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Test SSH Client")
    parser.add_argument("host", help="SSH server hostname")
    parser.add_argument("port", type=int, help="SSH server port")
    parser.add_argument("username", help="SSH username")
    parser.add_argument("password", help="SSH password")

    args = parser.parse_args()

    asyncio.run(test_ssh_client(args.host, args.port, args.username, args.password))
