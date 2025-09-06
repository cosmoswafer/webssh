const PRIVATE_KEY_STORAGE_KEY = "webssh_private_key";

const term = new Terminal({
  termName: "xterm-256color",
});
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
    if (socket && socket.readyState === WebSocket.OPEN) {
      const resizeMessage = JSON.stringify({
        type: "resize",
        cols: term.cols,
        rows: term.rows,
      });
      socket.send(resizeMessage);
    }
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

  // Set focus on the password input field
  document.getElementById("password").focus();

  fitTerminal();
  window.addEventListener("resize", fitTerminal);

  const authMethodRadios = document.querySelectorAll(
    'input[name="auth-method"]',
  );
  const passwordField = document.getElementById("password-field");
  const privateKeyField = document.getElementById("private-key-field");

  for (const radio of authMethodRadios) {
    radio.addEventListener("change", () => {
      if (radio.value === "password") {
        passwordField.style.display = "block";
        privateKeyField.style.display = "none";
        document.getElementById("password").value = "";
        document.getElementById("password").focus();
      } else {
        passwordField.style.display = "none";
        privateKeyField.style.display = "block";
        const savedKey = localStorage.getItem(PRIVATE_KEY_STORAGE_KEY);
        if (savedKey) {
          document.getElementById("private-key").value = savedKey;
        }
      }
    });
  }

  document.getElementById("private-key").addEventListener("input", (e) => {
    localStorage.setItem(PRIVATE_KEY_STORAGE_KEY, e.target.value);
  });

  document.getElementById("private-key").addEventListener("input", (e) => {
    localStorage.setItem(PRIVATE_KEY_STORAGE_KEY, e.target.value);
  });

  sshForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const host = document.getElementById("host").value;
    const port = document.getElementById("port").value;
    const username = document.getElementById("username").value;
    const password = document.getElementById("password").value;
    const privateKey = document.getElementById("private-key").value;
    const authMethod = document.querySelector(
      'input[name="auth-method"]:checked',
    ).value;

    const isLocalhost =
      window.location.hostname === "localhost" ||
      window.location.hostname === "127.0.0.1";
    const protocol = isLocalhost ? "ws://" : "wss://";
    socket = new WebSocket(`${protocol}${window.location.host}/connect`);

    socket.onopen = () => {
      console.log("WebSocket connection established");
      const connectionData = JSON.stringify({
        host,
        port,
        username,
        password,
        privateKey,
        authMethod,
      });
      socket.send(connectionData);
      document.getElementById("ssh-form").classList.add("is-hidden");
      fitTerminal();
      // Focus on the terminal after form is hidden
      term.focus();
    };

    socket.onmessage = (event) => {
      console.log("Received message:", event.data);
      term.write(event.data);
    };

    socket.onclose = (event) => {
      console.log("WebSocket connection closed:", event.code, event.reason);
      term.write("\r\nDisconnected from SSH server\r\n");
      document.getElementById("ssh-form").classList.remove("is-hidden");
      fitTerminal();
    };

    socket.onerror = (error) => {
      console.error("WebSocket error:", error);
      term.write(`\r\nError: ${error.message}\r\n`);
    };
  });

  term.onData((data) => {
    if (socket && socket.readyState === WebSocket.OPEN) {
      // Handle special cases for Enter and Ctrl+C
      if (data === "\r") {
        socket.send("\n");
      } else {
        socket.send(data);
      }
    }
  });

  // Assuming 'term' is your xterm.js instance and 'socket' is your WebSocket
  term.onResize((size) => {
    const cols = size.cols;
    const rows = size.rows;

    // Debug messages
    console.log(`Terminal resized to ${cols} cols and ${rows} rows`);

    // Send the new size to the server
    const resizeMessage = JSON.stringify({
      type: "resize",
      cols: cols,
      rows: rows,
    });
    console.log(`Sending resize message: ${resizeMessage}`);
    socket.send(resizeMessage);
  });
});
