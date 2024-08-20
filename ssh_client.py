import asyncio
import paramiko
import getpass

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
        await asyncio.get_event_loop().run_in_executor(
            None, self._connect
        )
        self.channel = self.client.invoke_shell()
        self.channel.setblocking(0)

    def _connect(self):
        if self.password is None:
            self.password = getpass.getpass(f"Enter password for {self.username}@{self.host}: ")
        
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
