const term = new Terminal();
const fitAddon = new FitAddon.FitAddon();
term.loadAddon(fitAddon);

let socket;

document.addEventListener("DOMContentLoaded", () => {
  const terminalElement = document.getElementById("terminal");
  const sshForm = document.getElementById("ssh-form");

  term.open(terminalElement);

  function fitTerminal() {
    fitAddon.fit();
    term.resize(term.cols, term.rows);
  }

  function getQueryParams() {
    const params = new URLSearchParams(window.location.search);
    return {
      host: params.get("host"),
      port: params.get("port"),
      username: params.get("username"),
    };
  }

  function populateFormFromQueryParams() {
    const params = getQueryParams();
    if (params.host) document.getElementById("host").value = params.host;
    if (params.port) document.getElementById("port").value = params.port;
    if (params.username)
      document.getElementById("username").value = params.username;
  }

  populateFormFromQueryParams();

  fitTerminal();
  window.addEventListener("resize", fitTerminal);

  sshForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const host = document.getElementById("host").value;
    const port = document.getElementById("port").value;
    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;

    socket = new WebSocket(`ws://${window.location.host}/connect?host=${host}&port=${port}&username=${username}&password=${password}`);

      socket.onopen = () => {
        term.write("Connected to SSH server\r\n");
        sshForm.classList.add("hidden");
        fitTerminal();
      };

      socket.onmessage = (event) => {
        term.write(event.data);
      };

      socket.onclose = () => {
        term.write("\r\nDisconnected from SSH server\r\n");
        sshForm.classList.remove("hidden");
        fitTerminal();
      };

      term.onData((data) => {
        socket.send(data);
      });
    } else {
      const errorMessage = await response.text();
      term.write(`Failed to connect to SSH server: ${errorMessage}\r\n`);
    }
  });
});
