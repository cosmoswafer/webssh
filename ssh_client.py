import asyncio
import json
import paramiko
import io
from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

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
        passphrase = self.password
        if isinstance(passphrase, bytes):
            passphrase_for_paramiko = passphrase.decode("utf-8")
            passphrase_for_cryptography = passphrase
        elif isinstance(passphrase, str):
            passphrase_for_paramiko = passphrase
            passphrase_for_cryptography = passphrase.encode("utf-8")
        else:
            passphrase_for_paramiko = None
            passphrase_for_cryptography = None
        
        # Try different key types in order of common usage
        key_types = [
            paramiko.RSAKey,
            paramiko.Ed25519Key,
            paramiko.ECDSAKey
        ]
        
        for key_type in key_types:
            try:
                key_io.seek(0)  # Reset stream position
                return key_type.from_private_key(key_io, password=passphrase_for_paramiko)
            except (paramiko.SSHException, paramiko.PasswordRequiredException):
                continue

        # Fallback for PKCS8/PEM Ed25519 keys by converting to OpenSSH format.
        fallback_error = None
        try:
            loaded_key = serialization.load_pem_private_key(
                private_key_str.encode("utf-8"),
                password=passphrase_for_cryptography,
            )
            if isinstance(loaded_key, Ed25519PrivateKey):
                openssh_key = loaded_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.OpenSSH,
                    encryption_algorithm=serialization.NoEncryption(),
                ).decode("utf-8")
                return paramiko.Ed25519Key.from_private_key(io.StringIO(openssh_key))
        except (TypeError, ValueError, UnsupportedAlgorithm) as error:
            fallback_error = error
        
        # If all key types failed, raise a descriptive error
        message = "Unsupported private key format. Please ensure you're using a valid SSH private key (RSA, Ed25519, or ECDSA)."
        if fallback_error:
            raise SSHClientException(
                f"{message} PEM/PKCS8 Ed25519 parsing also failed: {fallback_error}"
            ) from fallback_error
        raise SSHClientException(message)

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
