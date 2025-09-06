const PRIVATE_KEY_STORAGE_KEY = "webssh_private_key";

// Solarized Dark theme colors
const solarizedDarkTheme = {
  background: '#002b36',     // base03
  foreground: '#839496',     // base0
  cursor: '#93a1a1',         // base1
  cursorAccent: '#002b36',   // base03
  selection: '#073642',      // base02
  black: '#073642',          // base02
  red: '#dc322f',            // red
  green: '#859900',          // green
  yellow: '#b58900',         // yellow
  blue: '#268bd2',           // blue
  magenta: '#d33682',        // magenta
  cyan: '#2aa198',           // cyan
  white: '#eee8d5',          // base2
  brightBlack: '#586e75',    // base01
  brightRed: '#cb4b16',      // orange
  brightGreen: '#93a1a1',    // base1
  brightYellow: '#657b83',   // base00
  brightBlue: '#839496',     // base0
  brightMagenta: '#6c71c4',  // violet
  brightCyan: '#93a1a1',     // base1
  brightWhite: '#fdf6e3'     // base3
};

// Solarized Light theme colors
const solarizedLightTheme = {
  background: '#fdf6e3',     // base3
  foreground: '#657b83',     // base00
  cursor: '#586e75',         // base01
  cursorAccent: '#fdf6e3',   // base3
  selection: '#eee8d5',      // base2
  black: '#073642',          // base02
  red: '#dc322f',            // red
  green: '#859900',          // green
  yellow: '#b58900',         // yellow
  blue: '#268bd2',           // blue
  magenta: '#d33682',        // magenta
  cyan: '#2aa198',           // cyan
  white: '#eee8d5',          // base2
  brightBlack: '#586e75',    // base01
  brightRed: '#cb4b16',      // orange
  brightGreen: '#93a1a1',    // base1
  brightYellow: '#657b83',   // base00
  brightBlue: '#839496',     // base0
  brightMagenta: '#6c71c4',  // violet
  brightCyan: '#93a1a1',     // base1
  brightWhite: '#fdf6e3'     // base3
};

// Use solarized dark by default
const term = new Terminal({
  termName: "xterm-256color",
  theme: solarizedDarkTheme,
});

// Function to switch between solarized themes (can be called from browser console)
// Usage: 
//   switchSolarizedTheme(true)  - Switch to solarized light theme
//   switchSolarizedTheme(false) - Switch to solarized dark theme
function switchSolarizedTheme(useLightTheme = false) {
  const theme = useLightTheme ? solarizedLightTheme : solarizedDarkTheme;
  term.options.theme = theme;
  console.log(`Switched to solarized ${useLightTheme ? 'light' : 'dark'} theme`);
}

// Make theme switching available globally for easy access
window.switchSolarizedTheme = switchSolarizedTheme;
const fitAddon = new FitAddon();
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
