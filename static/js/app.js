const term = new Terminal();
const fitAddon = new FitAddon.FitAddon();
term.loadAddon(fitAddon);

let socket;

document.addEventListener('DOMContentLoaded', () => {
    term.open(document.getElementById('terminal'));
    fitAddon.fit();

    window.addEventListener('resize', () => {
        fitAddon.fit();
    });

    document.getElementById('ssh-form').addEventListener('submit', async (e) => {
        e.preventDefault();
        const host = document.getElementById('host').value;
        const port = document.getElementById('port').value;
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;

        const response = await fetch('/connect', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ host, port, username, password }),
        });

        if (response.ok) {
            socket = new WebSocket(`ws://${window.location.host}/connect`);
            
            socket.onopen = () => {
                term.write('Connected to SSH server\r\n');
            };

            socket.onmessage = (event) => {
                term.write(event.data);
            };

            socket.onclose = () => {
                term.write('\r\nDisconnected from SSH server\r\n');
            };

            term.onData((data) => {
                socket.send(data);
            });
        } else {
            term.write('Failed to connect to SSH server\r\n');
        }
    });
});
