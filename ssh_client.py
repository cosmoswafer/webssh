import asyncio
import paramiko
import getpass

class SSHClientException(Exception):
    pass

class SSHClient:
    def __init__(self, host, port, username, password=None):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.channel = None

    async def connect(self):
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, self._connect
            )
            self.channel = self.client.invoke_shell()
            self.channel.setblocking(0)
        except paramiko.AuthenticationException:
            # If authentication fails, try to prompt for password
            if self.password is None:
                self.password = await asyncio.get_event_loop().run_in_executor(
                    None, getpass.getpass, f"Enter password for {self.username}@{self.host}: "
                )
                # Try to connect again with the new password
                await self.connect()
            else:
                raise SSHClientException("Authentication failed. Please check your credentials.")
        except paramiko.SSHException as e:
            raise SSHClientException(f"SSH connection failed: {str(e)}")
        except Exception as e:
            raise SSHClientException(f"An unexpected error occurred: {str(e)}")

    def _connect(self):
        self.client.connect(
            self.host,
            port=self.port,
            username=self.username,
            password=self.password
        )

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

    async def close(self):
        self.client.close()
