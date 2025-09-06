import asyncio
import json
import paramiko
import io

class SSHClientException(Exception):
    pass

class SSHClient:
    def __init__(self, host, port, username, password=None, private_key=None):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.private_key = private_key
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.channel = None

    async def connect(self):
        try:
            await asyncio.get_event_loop().run_in_executor(None, self._connect)
            self.channel = self.client.invoke_shell(term='xterm-256color')
            self.channel.setblocking(0)
        except paramiko.AuthenticationException:
            raise SSHClientException("Authentication failed. Please check your credentials.")
        except paramiko.SSHException as e:
            raise SSHClientException(f"SSH connection failed: {str(e)}")
        except Exception as e:
            raise SSHClientException(f"An unexpected error occurred: {str(e)}")

    def _connect(self):
        if self.private_key:
            pkey = self._load_private_key(self.private_key)
            self.client.connect(
                self.host,
                port=self.port,
                username=self.username,
                pkey=pkey,
                allow_agent=False,
                look_for_keys=False
            )
        else:
            self.client.connect(
                self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                allow_agent=True,
                look_for_keys=True
            )

    def _load_private_key(self, private_key_str):
        """Load a private key from string, supporting multiple key types."""
        key_io = io.StringIO(private_key_str)
        
        # Try different key types in order of common usage
        key_types = [
            paramiko.RSAKey,
            paramiko.Ed25519Key,
            paramiko.ECDSAKey
        ]
        
        for key_type in key_types:
            try:
                key_io.seek(0)  # Reset stream position
                return key_type.from_private_key(key_io)
            except Exception:
                continue
        
        # If all key types failed, raise a descriptive error
        raise SSHClientException("Unsupported private key format. Please ensure you're using a valid SSH private key (RSA, Ed25519, or ECDSA).")

    async def read_output(self):
        if self.channel.recv_ready():
            return await asyncio.get_event_loop().run_in_executor(
                None, self.channel.recv, 1024
            )
        return None

    async def send_input(self, data):
        await asyncio.get_event_loop().run_in_executor(
            None, self.channel.send, data
        )

    async def handle_resize(self, cols, rows):
        await asyncio.get_event_loop().run_in_executor(
            None, self.channel.resize_pty, cols, rows
        )

    async def close(self):
        if self.channel:
            self.channel.close()
        if self.client:
            self.client.close()
