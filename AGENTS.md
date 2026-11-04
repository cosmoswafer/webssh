# WebSSH Rust agent notes

## Commands

- Run from the repository root: static assets are read from `./index.html` and `./static/`. Start with `cargo run` or `cargo run --release`. `PORT` overrides the default port 8080; `.env` is not loaded automatically.
- Run all tests with `cargo test`. Focus by name with `cargo test <test_name>`, by integration-test target with `cargo test --test <target>`, or by workspace package with `cargo test -p <package>`.
- Require this quality gate after code changes:
  ```sh
  cargo fmt --check
  cargo clippy --all-targets --all-features -- -D warnings
  cargo test
  ```
- No frontend build is configured; Xterm.js and Bulma load from CDNs. `ssh2` uses vendored OpenSSL/libssh2, so a C build toolchain is required but system OpenSSL development packages are not.

## Architecture and invariants

- `main.rs` starts Axum; `server.rs` owns static routes and `/connect`; `protocol.rs` validates external messages; `ssh.rs` owns SSH authentication and I/O; `config.rs`/`port.rs` parse environment configuration.
- `ssh2` is synchronous: every connection has a dedicated OS worker thread and bounded Tokio channels to the async relay. Never call blocking SSH operations directly on Tokio executor threads. Nonblocking writes have deadlines; PTY resize retries libssh2 `EAGAIN`.
- Browser flow is `index.html` + `static/js/app.js` -> WebSocket `/connect` -> SSH worker. The first text frame is connection JSON; later frames are raw terminal input or JSON resize messages. Keep credential, `sessionMode`, and resize fields synchronized with `protocol.rs`.
- Supported session modes are `none`, `screen`, and `tmux`. Preserve the legacy `enableScreenSession` payload and frontend `"true"`/`"false"` localStorage preferences.
- `screen`/`tmux` startup drains initial shell output until a quiet period before sending its command. Changing this ordering affects startup and visible banners/prompts.
- The frontend persists private keys and session-mode preferences in localStorage. SSH host keys are not verified, and agent/default-key fallback can use server-side identities; do not accidentally document these as hardened behaviors.

## Minimum std-dev workflow

Follow the copied [std-dev skill](.agents/skills/std-dev/SKILL.md) for every non-trivial change:

1. **Probe only if needed:** for an external API with unknown response shapes, collect real responses first; otherwise reproduce the bug or use existing schemas/docs.
2. **Plan the data flow:** identify external boundaries, canonical shared structures, transformation/validation points, and invariants. Get plan approval before non-trivial implementation.
3. **Define types first:** parse external input into canonical Rust types at subsystem boundaries; use fallible constructors/newtypes to make invalid states unrepresentable. Do not pass raw strings or loose maps inward.
4. **Implement incrementally:** types -> core logic -> wiring. Keep dependencies directed inward, modules cohesive, and the change scoped to the root cause.
5. **Test:** add focused unit tests mirroring the source structure and run the full quality gate above. Perform frontend/UI verification only when explicitly requested.
6. **Commit/push only after explicit confirmation for that mutation.** Use conventional commits describing the why; do not use issue auto-closing keywords.
