use thiserror::Error;

use crate::port::{InvalidPort, Port};

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct Config {
    port: Port,
}

#[derive(Clone, Debug, Error, Eq, PartialEq)]
#[error("invalid PORT: {0}")]
pub struct ConfigError(#[from] InvalidPort);

impl Config {
    pub fn from_env() -> Result<Self, ConfigError> {
        let port = std::env::var("PORT").ok();
        Self::from_port_value(port.as_deref())
    }

    fn from_port_value(value: Option<&str>) -> Result<Self, ConfigError> {
        let port = match value {
            Some(value) => value.parse().map_err(ConfigError)?,
            None => Port::HTTP_DEFAULT,
        };
        Ok(Self { port })
    }

    pub const fn port(self) -> Port {
        self.port
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn defaults_to_8080() {
        assert_eq!(
            Config::from_port_value(None).unwrap().port(),
            Port::HTTP_DEFAULT
        );
    }

    #[test]
    fn parses_and_validates_port() {
        assert_eq!(
            Config::from_port_value(Some("9000")).unwrap().port().get(),
            9000
        );
        assert!(Config::from_port_value(Some("invalid")).is_err());
        assert!(Config::from_port_value(Some("0")).is_err());
    }
}
