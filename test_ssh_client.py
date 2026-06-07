import asyncio
import contextlib
import sys
import argparse
import unittest
from unittest.mock import AsyncMock, patch
from aiohttp import web
from ssh_client import SSHClient, SSHClientException
from ssh_handler import handle_ssh_connection as handle_ws_ssh_connection, normalize_session_mode

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
    import tempfile

    # Allow test keys directory to be set via environment variable for portability
    test_keys_dir = os.environ.get("TEST_KEYS_DIR")
    if not test_keys_dir:
        print("⚠ TEST_KEYS_DIR environment variable not set. Skipping key loading tests.")
        return
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


class TestSSHClientSessionCommands(unittest.IsolatedAsyncioTestCase):
    async def test_start_session_uses_screen_command(self):
        client = SSHClient("test.example.com", 22, "testuser")
        client.send_input = AsyncMock()

        await client.start_session("screen")

        client.send_input.assert_awaited_once_with("screen -DR WEBSSH_AUTO\n")

    async def test_start_session_uses_tmux_command(self):
        client = SSHClient("test.example.com", 22, "testuser")
        client.send_input = AsyncMock()

        await client.start_session("tmux")

        client.send_input.assert_awaited_once_with("tmux new-session -A -s WEBSSH_AUTO\n")

    async def test_start_session_rejects_invalid_mode(self):
        client = SSHClient("test.example.com", 22, "testuser")

        with self.assertRaises(SSHClientException):
            await client.start_session("invalid")


class TestSessionModeHandling(unittest.IsolatedAsyncioTestCase):
    def test_normalize_session_mode_supports_new_and_legacy_values(self):
        self.assertEqual(normalize_session_mode({"sessionMode": "screen"}), "screen")
        self.assertEqual(normalize_session_mode({"sessionMode": "tmux"}), "tmux")
        self.assertEqual(normalize_session_mode({"enableScreenSession": True}), "screen")
        self.assertEqual(normalize_session_mode({}), "none")

    async def test_handle_connection_starts_requested_session(self):
        ws = AsyncMock()
        data = {
            "host": "example.com",
            "port": 22,
            "username": "demo",
            "sessionMode": "tmux",
        }

        mock_ssh_client = AsyncMock()
        mock_ssh_client.read_output.side_effect = [b"", asyncio.CancelledError()]
        create_task = asyncio.create_task
        background_tasks = []

        def create_cancelled_task(coro):
            task = create_task(coro)
            task.cancel()
            background_tasks.append(task)
            return task

        with patch("ssh_handler.SSHClient", return_value=mock_ssh_client), patch(
            "ssh_handler.asyncio.create_task",
            side_effect=create_cancelled_task,
        ):
            result = await handle_ws_ssh_connection(ws, data)

        for task in background_tasks:
            with contextlib.suppress(asyncio.CancelledError):
                await task

        self.assertIs(result, mock_ssh_client)
        mock_ssh_client.connect.assert_awaited_once()
        mock_ssh_client.start_session.assert_awaited_once_with("tmux")

    async def test_handle_connection_returns_error_for_invalid_session_mode(self):
        ws = AsyncMock()
        data = {
            "host": "example.com",
            "port": 22,
            "username": "demo",
            "sessionMode": "invalid",
        }

        response = await handle_ws_ssh_connection(ws, data)

        self.assertIsInstance(response, web.Response)
        self.assertEqual(response.status, 400)
        self.assertIn("Unsupported session mode", response.text)

if __name__ == "__main__": 
    if len(sys.argv) > 1 and sys.argv[1] == "--test-keys":
        test_private_key_loading()
    else:
        asyncio.run(main())
