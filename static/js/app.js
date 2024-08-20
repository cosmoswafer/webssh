const term = new Terminal();
const fitAddon = new FitAddon.FitAddon();
term.loadAddon(fitAddon);

let socket;

document.addEventListener('DOMContentLoaded', () => {
    const terminalElement = document.getElementById('terminal');
    const sshForm = document.getElementById('ssh-form');

    term.open(terminalElement);
    
    function fitTerminal() {
        fitAddon.fit();
        term.resize(term.cols, term.rows);
    }

    fitTerminal();
    window.addEventListener('resize', fitTerminal);

    sshForm.addEventListener('submit', async (e) => {
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
                sshForm.classList.add('hidden');
                fitTerminal();
            };

            socket.onmessage = (event) => {
                term.write(event.data);
            };

            socket.onclose = () => {
                term.write('\r\nDisconnected from SSH server\r\n');
                sshForm.classList.remove('hidden');
                fitTerminal();
            };

            term.onData((data) => {
                socket.send(data);
            });
        } else {
            term.write('Failed to connect to SSH server\r\n');
        }
    });
});
