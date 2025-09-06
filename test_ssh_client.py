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

def test_private_key_loading():
    """Test that private key loading works for different key types."""
    import os
    
    # Test with our generated test keys if available
    test_keys_dir = "/tmp/test_keys"
    key_files = {
        "RSA": f"{test_keys_dir}/test_rsa",
        "Ed25519": f"{test_keys_dir}/test_ed25519", 
        "ECDSA": f"{test_keys_dir}/test_ecdsa"
    }
    
    for key_type, key_file in key_files.items():
        if os.path.exists(key_file):
            with open(key_file, 'r') as f:
                private_key = f.read()
            
            client = SSHClient("test.example.com", 22, "testuser", private_key=private_key)
            try:
                pkey = client._load_private_key(private_key)
                print(f"✓ {key_type} key loading test passed: {type(pkey).__name__}")
            except Exception as e:
                print(f"✗ {key_type} key loading test failed: {e}")
        else:
            print(f"⚠ {key_type} test key not found at {key_file}")
    
    # Test invalid key handling
    invalid_key = "invalid key content"
    client = SSHClient("test.example.com", 22, "testuser", private_key=invalid_key)
    try:
        client._load_private_key(invalid_key)
        print("✗ Invalid key test failed: should have raised exception")
    except SSHClientException as e:
        print(f"✓ Invalid key test passed: {e}")
    except Exception as e:
        print(f"✗ Invalid key test failed with unexpected error: {e}")

if __name__ == "__main__": 
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--test-keys":
        test_private_key_loading()
    else:
        asyncio.run(main())
