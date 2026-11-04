use std::{
    fmt, fs,
    io::{self, ErrorKind, Read, Write},
    net::{TcpStream, ToSocketAddrs},
    path::PathBuf,
    thread,
    time::{Duration, Instant},
};

use ssh2::{Channel, ErrorCode, Session};
use thiserror::Error;
use tokio::sync::{mpsc, oneshot};

use crate::protocol::{ConnectRequest, ResizeRequest};

const IO_POLL_INTERVAL: Duration = Duration::from_millis(20);
const SHELL_POLL_INTERVAL: Duration = Duration::from_millis(50);
const SHELL_QUIET_PERIOD: Duration = Duration::from_millis(300);
const SHELL_READY_TIMEOUT: Duration = Duration::from_secs(10);
const CONNECT_TIMEOUT: Duration = Duration::from_secs(15);
const WRITE_TIMEOUT: Duration = Duration::from_secs(15);
const CHANNEL_QUEUE_SIZE: usize = 64;
const OUTPUT_QUEUE_SIZE: usize = 256;
// libssh2's public LIBSSH2_ERROR_EAGAIN value; ssh2 does not re-export the constant.
const LIBSSH2_ERROR_EAGAIN: i32 = -37;

#[derive(Clone, Debug, Error, Eq, PartialEq)]
pub enum SshError {
    #[error("authentication failed; check the credentials, private key, and passphrase")]
    Authentication,
    #[error("{0}")]
    Connection(String),
}

impl SshError {
    fn connection(context: &str, error: impl fmt::Display) -> Self {
        Self::Connection(format!("{context}: {error}"))
    }
}

#[derive(Debug)]
pub enum SshEvent {
    Output(String),
    Error(SshError),
    Closed,
}

enum Command {
    Input(String),
    Resize(ResizeRequest),
    Close,
}

pub struct SshSender {
    commands: mpsc::Sender<Command>,
}

impl SshSender {
    pub async fn send_input(&self, input: String) -> Result<(), SshError> {
        self.send(Command::Input(input)).await
    }

    pub async fn resize(&self, resize: ResizeRequest) -> Result<(), SshError> {
        self.send(Command::Resize(resize)).await
    }

    async fn send(&self, command: Command) -> Result<(), SshError> {
        self.commands
            .send(command)
            .await
            .map_err(|_| SshError::Connection("SSH connection is no longer available".into()))
    }
}

impl Drop for SshSender {
    fn drop(&mut self) {
        let _ = self.commands.try_send(Command::Close);
    }
}

pub struct SshSession {
    sender: SshSender,
    events: mpsc::Receiver<SshEvent>,
}

impl SshSession {
    pub async fn connect(request: ConnectRequest) -> Result<Self, SshError> {
        let (commands, command_rx) = mpsc::channel(CHANNEL_QUEUE_SIZE);
        let (event_tx, events) = mpsc::channel(OUTPUT_QUEUE_SIZE);
        let (startup_tx, startup_rx) = oneshot::channel();

        thread::Builder::new()
            .name("webssh-ssh".into())
            .spawn(move || {
                let worker = match Worker::connect(request) {
                    Ok(worker) => worker,
                    Err(error) => {
                        let _ = startup_tx.send(Err(error));
                        return;
                    }
                };

                if startup_tx.send(Ok(())).is_err() {
                    return;
                }

                if let Err(error) = worker.run(command_rx, &event_tx) {
                    let _ = event_tx.blocking_send(SshEvent::Error(error));
                }
                let _ = event_tx.blocking_send(SshEvent::Closed);
            })
            .map_err(|error| SshError::connection("failed to start SSH worker", error))?;

        match startup_rx.await {
            Ok(result) => result.map(|()| Self {
                sender: SshSender { commands },
                events,
            }),
            Err(_) => Err(SshError::Connection(
                "SSH worker stopped during connection".into(),
            )),
        }
    }

    pub fn split(self) -> (SshSender, mpsc::Receiver<SshEvent>) {
        (self.sender, self.events)
    }
}

struct Worker {
    channel: Channel,
}

impl Worker {
    fn connect(request: ConnectRequest) -> Result<Self, SshError> {
        let tcp = connect_tcp(request.host(), request.port().get())?;
        let mut session = Session::new()
            .map_err(|error| SshError::connection("failed to create SSH session", error))?;
        session.set_timeout(duration_millis(CONNECT_TIMEOUT));
        session.set_tcp_stream(tcp);
        session
            .handshake()
            .map_err(|error| SshError::connection("SSH handshake failed", error))?;

        authenticate(&session, &request)?;

        let mut channel = session
            .channel_session()
            .map_err(|error| SshError::connection("failed to open SSH channel", error))?;
        channel
            .request_pty("xterm-256color", None, Some((80, 24, 0, 0)))
            .map_err(|error| SshError::connection("failed to allocate terminal", error))?;
        channel
            .shell()
            .map_err(|error| SshError::connection("failed to start remote shell", error))?;

        session.set_blocking(false);
        if let Some(command) = request.session_mode().startup_command() {
            wait_for_shell_ready(&mut channel)?;
            write_nonblocking(&mut channel, command).map_err(|error| {
                SshError::connection("failed to start session multiplexer", error)
            })?;
        }

        Ok(Self { channel })
    }

    fn run(
        mut self,
        mut commands: mpsc::Receiver<Command>,
        events: &mpsc::Sender<SshEvent>,
    ) -> Result<(), SshError> {
        let mut buffer = [0_u8; 8192];

        loop {
            loop {
                match commands.try_recv() {
                    Ok(Command::Input(input)) => {
                        write_nonblocking(&mut self.channel, input.as_bytes()).map_err(
                            |error| SshError::connection("failed to send terminal input", error),
                        )?;
                    }
                    Ok(Command::Resize(resize)) => {
                        resize_nonblocking(&mut self.channel, resize.cols(), resize.rows())
                            .map_err(|error| {
                                SshError::connection("failed to resize terminal", error)
                            })?
                    }
                    Ok(Command::Close) => {
                        let _ = self.channel.close();
                        return Ok(());
                    }
                    Err(mpsc::error::TryRecvError::Empty) => break,
                    Err(mpsc::error::TryRecvError::Disconnected) => {
                        let _ = self.channel.close();
                        return Ok(());
                    }
                }
            }

            loop {
                match self.channel.read(&mut buffer) {
                    Ok(0) => break,
                    Ok(read) => {
                        let output = String::from_utf8_lossy(&buffer[..read]).into_owned();
                        if events.blocking_send(SshEvent::Output(output)).is_err() {
                            let _ = self.channel.close();
                            return Ok(());
                        }
                        if read < buffer.len() {
                            break;
                        }
                    }
                    Err(error) if error.kind() == ErrorKind::WouldBlock => break,
                    Err(error) => {
                        return Err(SshError::connection("failed to read SSH output", error));
                    }
                }
            }

            if self.channel.eof() {
                return Ok(());
            }

            thread::sleep(IO_POLL_INTERVAL);
        }
    }
}

fn connect_tcp(host: &str, port: u16) -> Result<TcpStream, SshError> {
    let addresses = (host, port)
        .to_socket_addrs()
        .map_err(|error| SshError::connection("failed to resolve SSH host", error))?;
    let mut last_error = None;

    for address in addresses {
        match TcpStream::connect_timeout(&address, CONNECT_TIMEOUT) {
            Ok(stream) => return Ok(stream),
            Err(error) => last_error = Some(error),
        }
    }

    let error = last_error
        .map(|error| error.to_string())
        .unwrap_or_else(|| "host resolved to no addresses".into());
    Err(SshError::Connection(format!(
        "failed to connect to {host}:{port}: {error}"
    )))
}

fn authenticate(session: &Session, request: &ConnectRequest) -> Result<(), SshError> {
    let result = if let Some(private_key) = request.private_key() {
        session.userauth_pubkey_memory(request.username(), None, private_key, request.password())
    } else if let Some(password) = request.password() {
        session
            .userauth_password(request.username(), password)
            .or_else(|_| authenticate_agent_or_default_keys(session, request))
    } else {
        authenticate_agent_or_default_keys(session, request)
    };

    if result.is_err() || !session.authenticated() {
        return Err(SshError::Authentication);
    }
    Ok(())
}

fn authenticate_agent_or_default_keys(
    session: &Session,
    request: &ConnectRequest,
) -> Result<(), ssh2::Error> {
    let agent_result = session.userauth_agent(request.username());
    if agent_result.is_ok() && session.authenticated() {
        return Ok(());
    }

    let mut last_error = agent_result.err();
    for path in default_private_key_paths() {
        match session.userauth_pubkey_file(request.username(), None, &path, request.password()) {
            Ok(()) if session.authenticated() => return Ok(()),
            Ok(()) => {}
            Err(error) => last_error = Some(error),
        }
    }

    Err(last_error.unwrap_or_else(ssh2::Error::unknown))
}

fn default_private_key_paths() -> Vec<PathBuf> {
    let Some(home) = std::env::var_os("HOME") else {
        return Vec::new();
    };
    let ssh_dir = PathBuf::from(home).join(".ssh");
    ["id_ed25519", "id_rsa", "id_ecdsa"]
        .into_iter()
        .filter_map(|name| {
            let path = ssh_dir.join(name);
            fs::metadata(&path).is_ok().then_some(path)
        })
        .collect()
}

const fn duration_millis(duration: Duration) -> u32 {
    duration.as_millis() as u32
}

fn write_nonblocking(channel: &mut Channel, mut data: &[u8]) -> io::Result<()> {
    let deadline = Instant::now() + WRITE_TIMEOUT;

    while !data.is_empty() {
        if channel.eof() {
            return Err(io::Error::new(
                ErrorKind::UnexpectedEof,
                "SSH channel closed while sending data",
            ));
        }

        match channel.write(data) {
            Ok(0) => {
                return Err(io::Error::new(
                    ErrorKind::WriteZero,
                    "SSH channel accepted no data",
                ));
            }
            Ok(written) => data = &data[written..],
            Err(error) if error.kind() == ErrorKind::WouldBlock => {
                if Instant::now() >= deadline {
                    return Err(io::Error::new(
                        ErrorKind::TimedOut,
                        "timed out sending data to SSH channel",
                    ));
                }
                thread::sleep(IO_POLL_INTERVAL);
            }
            Err(error) => return Err(error),
        }
    }
    Ok(())
}

fn resize_nonblocking(channel: &mut Channel, cols: u32, rows: u32) -> Result<(), ssh2::Error> {
    let deadline = Instant::now() + WRITE_TIMEOUT;

    loop {
        match channel.request_pty_size(cols, rows, None, None) {
            Err(error)
                if error.code() == ErrorCode::Session(LIBSSH2_ERROR_EAGAIN)
                    && Instant::now() < deadline =>
            {
                thread::sleep(IO_POLL_INTERVAL);
            }
            result => return result,
        }
    }
}

#[derive(Debug)]
struct ShellReadiness {
    started: Instant,
    last_output: Option<Instant>,
}

impl ShellReadiness {
    fn new(now: Instant) -> Self {
        Self {
            started: now,
            last_output: None,
        }
    }

    fn observe_output(&mut self, now: Instant) {
        self.last_output = Some(now);
    }

    fn should_finish(&self, now: Instant) -> bool {
        self.last_output
            .is_some_and(|last| now.duration_since(last) >= SHELL_QUIET_PERIOD)
            || now.duration_since(self.started) >= SHELL_READY_TIMEOUT
    }
}

fn wait_for_shell_ready(channel: &mut Channel) -> Result<(), SshError> {
    let mut readiness = ShellReadiness::new(Instant::now());
    let mut buffer = [0_u8; 4096];

    loop {
        match channel.read(&mut buffer) {
            Ok(0) if channel.eof() => {
                return Err(SshError::Connection(
                    "remote shell closed before it became ready".into(),
                ));
            }
            Ok(0) => {}
            Ok(_) => readiness.observe_output(Instant::now()),
            Err(error) if error.kind() == ErrorKind::WouldBlock => {}
            Err(error) => {
                return Err(SshError::connection(
                    "failed while waiting for remote shell",
                    error,
                ));
            }
        }

        if readiness.should_finish(Instant::now()) {
            return Ok(());
        }
        thread::sleep(SHELL_POLL_INTERVAL);
    }
}

#[cfg(test)]
mod tests {
    use crate::protocol::SessionMode;

    use super::*;

    #[test]
    fn shell_waits_for_a_quiet_period_after_output() {
        let start = Instant::now();
        let mut readiness = ShellReadiness::new(start);
        readiness.observe_output(start + Duration::from_millis(100));

        assert!(!readiness.should_finish(start + Duration::from_millis(399)));
        assert!(readiness.should_finish(start + Duration::from_millis(400)));
    }

    #[test]
    fn new_output_restarts_the_quiet_period() {
        let start = Instant::now();
        let mut readiness = ShellReadiness::new(start);
        readiness.observe_output(start);
        readiness.observe_output(start + Duration::from_millis(200));

        assert!(!readiness.should_finish(start + Duration::from_millis(300)));
        assert!(readiness.should_finish(start + Duration::from_millis(500)));
    }

    #[test]
    fn silent_shell_proceeds_after_timeout() {
        let start = Instant::now();
        let readiness = ShellReadiness::new(start);

        assert!(!readiness.should_finish(start + Duration::from_secs(9)));
        assert!(readiness.should_finish(start + SHELL_READY_TIMEOUT));
    }

    #[test]
    fn session_modes_keep_their_startup_contract() {
        assert_eq!(SessionMode::None.startup_command(), None);
        assert!(SessionMode::Screen.startup_command().is_some());
        assert!(SessionMode::Tmux.startup_command().is_some());
    }
}
