# Web-Based SSH Terminal

A web interface for interactive SSH sessions, built with Rust, Axum, WebSockets, and Xterm.js.

## Quick start

Requirements: stable Rust and a C build toolchain. OpenSSL and libssh2 are built from vendored sources by Cargo.

```sh
cargo run --release
```

Open `http://localhost:8080`, or prefill the connection form:

```text
http://localhost:8080?host=your_server&port=22&username=your_user
```

Set `PORT` to change the listen port:

```sh
PORT=9000 cargo run --release
```

Run from the repository root: the server reads `index.html` and `static/` from the current working directory. `.env` files are not loaded automatically.

## Connections

- Password authentication.
- Private-key authentication with an optional passphrase.
- SSH-agent and default `~/.ssh` key fallback when password authentication is absent or unsuccessful.
- Optional `screen` or `tmux` session attachment.
- Raw terminal input, UTF-8-lossy terminal output, and terminal resize forwarding.

The frontend sends its initial WebSocket message as JSON to `/connect`. Later text frames contain raw terminal input or resize messages such as:

```json
{"type":"resize","cols":80,"rows":24}
```

Session modes are `none`, `screen`, and `tmux`. The legacy `enableScreenSession` connection field remains supported.

## Frontend

`index.html` and `static/js/app.js` are served without a frontend build step. Xterm.js and Bulma load from CDNs, so a fully functional browser session needs access to those CDNs.

Themes can be selected with `?theme=light`, `?theme=dark`, or `?theme=auto`; the default is Solarized dark.

## Development

```sh
cargo test                         # all tests
cargo test <test_name>             # tests matching one name
cargo test --test <target>          # one integration-test target

cargo fmt --check
cargo clippy --all-targets --all-features -- -D warnings
cargo test
```

Unit tests cover protocol compatibility, validation, configuration, shell-readiness behavior, and static-file routes. End-to-end SSH verification requires a real SSH server; `screen` or `tmux` must be installed remotely when selected.

## Architecture

- `src/main.rs` — configuration, listener, and server startup.
- `src/protocol.rs` — validated connection and terminal-message types.
- `src/server.rs` — static routes and Axum WebSocket relay.
- `src/ssh.rs` — authentication and the blocking SSH worker.
- `src/port.rs` / `src/config.rs` — validated ports and `PORT` configuration.

Each SSH connection runs on a dedicated OS thread because `ssh2` is synchronous. Bounded Tokio channels connect that worker to the async Axum relay; SSH calls never run directly on an async executor thread.

## Security notes

- Use HTTPS/WSS through a TLS-enabled reverse proxy in production; the Axum server itself listens over HTTP.
- SSH host keys are not currently verified. Do not treat connections as protected against man-in-the-middle attacks until known-host verification is configured.
- Passwords and private keys are sent over the WebSocket. Private keys and session-mode preferences are persisted in browser localStorage; passwords are not.
- Agent/default-key fallback can use the server process's SSH identities. Restrict access to the web endpoint appropriately.
