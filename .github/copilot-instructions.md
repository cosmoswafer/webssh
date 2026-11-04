# WebSSH instructions

Follow the repository-root `AGENTS.md`, including its std-dev workflow.

- Rust/Axum backend; run from the repository root with `cargo run` (default port 8080).
- Keep `index.html` and `static/` as the no-build frontend; preserve its WebSocket protocol.
- `ssh2` is synchronous and belongs only on the dedicated SSH worker threads.
- Before finishing code changes, pass `cargo fmt --check`, `cargo clippy --all-targets --all-features -- -D warnings`, and `cargo test`.
