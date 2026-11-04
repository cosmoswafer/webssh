use std::fmt;

use serde::{Deserialize, Deserializer};
use serde_json::Value;
use thiserror::Error;

use crate::port::Port;

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct NonEmptyText(String);

impl NonEmptyText {
    fn new(value: String, field: &'static str) -> Result<Self, String> {
        if value.trim().is_empty() {
            return Err(format!("{field} must not be empty"));
        }
        Ok(Self(value))
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

fn deserialize_host<'de, D>(deserializer: D) -> Result<NonEmptyText, D::Error>
where
    D: Deserializer<'de>,
{
    NonEmptyText::new(String::deserialize(deserializer)?, "host").map_err(serde::de::Error::custom)
}

fn deserialize_username<'de, D>(deserializer: D) -> Result<NonEmptyText, D::Error>
where
    D: Deserializer<'de>,
{
    NonEmptyText::new(String::deserialize(deserializer)?, "username")
        .map_err(serde::de::Error::custom)
}

const fn default_ssh_port() -> Port {
    Port::SSH_DEFAULT
}

#[derive(Clone, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct ConnectRequest {
    #[serde(deserialize_with = "deserialize_host")]
    host: NonEmptyText,
    #[serde(default = "default_ssh_port")]
    port: Port,
    #[serde(deserialize_with = "deserialize_username")]
    username: NonEmptyText,
    #[serde(default)]
    password: Option<String>,
    #[serde(default)]
    private_key: Option<String>,
    #[serde(default)]
    session_mode: Option<SessionMode>,
    #[serde(default)]
    enable_screen_session: bool,
}

impl ConnectRequest {
    pub fn host(&self) -> &str {
        self.host.as_str()
    }

    pub const fn port(&self) -> Port {
        self.port
    }

    pub fn username(&self) -> &str {
        self.username.as_str()
    }

    pub fn password(&self) -> Option<&str> {
        self.password.as_deref().filter(|value| !value.is_empty())
    }

    pub fn private_key(&self) -> Option<&str> {
        self.private_key
            .as_deref()
            .filter(|value| !value.is_empty())
    }

    pub fn session_mode(&self) -> SessionMode {
        self.session_mode.unwrap_or(if self.enable_screen_session {
            SessionMode::Screen
        } else {
            SessionMode::None
        })
    }
}

impl fmt::Debug for ConnectRequest {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        formatter
            .debug_struct("ConnectRequest")
            .field("host", &self.host)
            .field("port", &self.port)
            .field("username", &self.username)
            .field("password", &self.password.as_ref().map(|_| "[REDACTED]"))
            .field(
                "private_key",
                &self.private_key.as_ref().map(|_| "[REDACTED]"),
            )
            .field("session_mode", &self.session_mode())
            .finish()
    }
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq)]
#[serde(rename_all = "lowercase")]
pub enum SessionMode {
    None,
    Screen,
    Tmux,
}

impl SessionMode {
    pub const fn startup_command(self) -> Option<&'static [u8]> {
        match self {
            Self::None => None,
            Self::Screen => Some(b"screen -DR WEBSSH_AUTO\n"),
            Self::Tmux => Some(b"tmux new-session -A -s WEBSSH_AUTO\n"),
        }
    }
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq)]
#[serde(try_from = "u32")]
pub struct TerminalDimension(u32);

impl TerminalDimension {
    const MAX: u32 = 10_000;

    pub const fn get(self) -> u32 {
        self.0
    }
}

impl TryFrom<u32> for TerminalDimension {
    type Error = String;

    fn try_from(value: u32) -> Result<Self, Self::Error> {
        if (1..=Self::MAX).contains(&value) {
            Ok(Self(value))
        } else {
            Err(format!(
                "terminal dimension must be between 1 and {}",
                Self::MAX
            ))
        }
    }
}

#[derive(Clone, Copy, Debug, Deserialize, Eq, PartialEq)]
pub struct ResizeRequest {
    cols: TerminalDimension,
    rows: TerminalDimension,
}

impl ResizeRequest {
    pub const fn cols(self) -> u32 {
        self.cols.get()
    }

    pub const fn rows(self) -> u32 {
        self.rows.get()
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum ClientMessage {
    Input(String),
    Resize(ResizeRequest),
}

#[derive(Debug, Error)]
pub enum ProtocolError {
    #[error("invalid connection request: {0}")]
    Connection(String),
    #[error("invalid resize request: {0}")]
    Resize(String),
}

pub fn parse_connect_request(text: &str) -> Result<ConnectRequest, ProtocolError> {
    let mut deserializer = serde_json::Deserializer::from_str(text);
    let request = serde_path_to_error::deserialize(&mut deserializer)
        .map_err(|error| ProtocolError::Connection(error.to_string()))?;
    deserializer
        .end()
        .map_err(|error| ProtocolError::Connection(error.to_string()))?;
    Ok(request)
}

pub fn parse_client_message(text: String) -> Result<ClientMessage, ProtocolError> {
    let Ok(value) = serde_json::from_str::<Value>(&text) else {
        return Ok(ClientMessage::Input(text));
    };

    if value.get("type").and_then(Value::as_str) != Some("resize") {
        return Ok(ClientMessage::Input(text));
    }

    let resize = serde_path_to_error::deserialize(value)
        .map_err(|error| ProtocolError::Resize(error.to_string()))?;
    Ok(ClientMessage::Resize(resize))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_the_existing_frontend_connection_payload() {
        let request = parse_connect_request(
            r#"{
                "host":"example.com",
                "port":"2222",
                "username":"demo",
                "password":"secret",
                "privateKey":"",
                "authMethod":"password",
                "sessionMode":"tmux"
            }"#,
        )
        .unwrap();

        assert_eq!(request.host(), "example.com");
        assert_eq!(request.port().get(), 2222);
        assert_eq!(request.username(), "demo");
        assert_eq!(request.password(), Some("secret"));
        assert_eq!(request.private_key(), None);
        assert_eq!(request.session_mode(), SessionMode::Tmux);
    }

    #[test]
    fn accepts_numeric_port_and_defaults_missing_port() {
        let numeric =
            parse_connect_request(r#"{"host":"example.com","port":22,"username":"demo"}"#).unwrap();
        let defaulted =
            parse_connect_request(r#"{"host":"example.com","username":"demo"}"#).unwrap();

        assert_eq!(numeric.port(), Port::SSH_DEFAULT);
        assert_eq!(defaulted.port(), Port::SSH_DEFAULT);
        assert_eq!(defaulted.session_mode(), SessionMode::None);
    }

    #[test]
    fn supports_legacy_screen_flag_without_overriding_explicit_mode() {
        let legacy = parse_connect_request(
            r#"{"host":"example.com","username":"demo","enableScreenSession":true}"#,
        )
        .unwrap();
        let explicit_none = parse_connect_request(
            r#"{"host":"example.com","username":"demo","enableScreenSession":true,"sessionMode":"none"}"#,
        )
        .unwrap();

        assert_eq!(legacy.session_mode(), SessionMode::Screen);
        assert_eq!(explicit_none.session_mode(), SessionMode::None);
    }

    #[test]
    fn rejects_invalid_connection_fields_with_field_context() {
        for (payload, field) in [
            (r#"{"host":" ","username":"demo"}"#, "host"),
            (r#"{"host":"example.com","username":""}"#, "username"),
            (
                r#"{"host":"example.com","username":"demo","port":0}"#,
                "port",
            ),
            (
                r#"{"host":"example.com","username":"demo","sessionMode":"invalid"}"#,
                "sessionMode",
            ),
        ] {
            let error = parse_connect_request(payload).unwrap_err().to_string();
            assert!(error.contains(field), "error {error:?} omitted {field}");
        }
    }

    #[test]
    fn connection_debug_output_redacts_secrets() {
        let request = parse_connect_request(
            r#"{"host":"example.com","username":"demo","password":"secret-password","privateKey":"secret-key"}"#,
        )
        .unwrap();
        let debug = format!("{request:?}");

        assert!(!debug.contains("secret-password"));
        assert!(!debug.contains("secret-key"));
        assert!(debug.contains("[REDACTED]"));
    }

    #[test]
    fn parses_resize_messages() {
        let message =
            parse_client_message(r#"{"type":"resize","cols":120,"rows":40}"#.into()).unwrap();

        let ClientMessage::Resize(resize) = message else {
            panic!("expected resize");
        };
        assert_eq!(resize.cols(), 120);
        assert_eq!(resize.rows(), 40);
    }

    #[test]
    fn preserves_raw_terminal_input_exactly() {
        for input in [
            "ls -la\n",
            "{\"type\":\"input\",\"data\":\"x\"}",
            "{\"type\":\"resize\"",
            "{\"notJson\":true",
        ] {
            assert_eq!(
                parse_client_message(input.into()).unwrap(),
                ClientMessage::Input(input.into())
            );
        }
    }

    #[test]
    fn rejects_invalid_resize_dimensions_and_missing_fields() {
        for payload in [
            r#"{"type":"resize","cols":0,"rows":24}"#,
            r#"{"type":"resize","cols":80}"#,
            r#"{"type":"resize","cols":"80","rows":24}"#,
        ] {
            assert!(
                parse_client_message(payload.into()).is_err(),
                "accepted {payload}"
            );
        }
    }

    #[test]
    fn session_commands_match_the_legacy_backend() {
        assert_eq!(SessionMode::None.startup_command(), None);
        assert_eq!(
            SessionMode::Screen.startup_command(),
            Some(b"screen -DR WEBSSH_AUTO\n".as_slice())
        );
        assert_eq!(
            SessionMode::Tmux.startup_command(),
            Some(b"tmux new-session -A -s WEBSSH_AUTO\n".as_slice())
        );
    }
}
