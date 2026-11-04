use std::{fmt, str::FromStr};

use serde::{Deserialize, Deserializer};
use thiserror::Error;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct Port(u16);

#[derive(Clone, Debug, Error, Eq, PartialEq)]
#[error("port must be an integer between 1 and 65535")]
pub struct InvalidPort;

impl Port {
    pub const SSH_DEFAULT: Self = Self(22);
    pub const HTTP_DEFAULT: Self = Self(8080);

    pub fn new(value: u64) -> Result<Self, InvalidPort> {
        let port = u16::try_from(value).map_err(|_| InvalidPort)?;
        if port == 0 {
            return Err(InvalidPort);
        }
        Ok(Self(port))
    }

    pub const fn get(self) -> u16 {
        self.0
    }
}

impl fmt::Display for Port {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        self.0.fmt(formatter)
    }
}

impl FromStr for Port {
    type Err = InvalidPort;

    fn from_str(value: &str) -> Result<Self, Self::Err> {
        let value = value.parse::<u64>().map_err(|_| InvalidPort)?;
        Self::new(value)
    }
}

impl<'de> Deserialize<'de> for Port {
    fn deserialize<D>(deserializer: D) -> Result<Self, D::Error>
    where
        D: Deserializer<'de>,
    {
        #[derive(Deserialize)]
        #[serde(untagged)]
        enum WirePort {
            Number(u64),
            Text(String),
        }

        match WirePort::deserialize(deserializer)? {
            WirePort::Number(value) => Self::new(value).map_err(serde::de::Error::custom),
            WirePort::Text(value) => value.parse().map_err(serde::de::Error::custom),
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn accepts_string_and_numeric_ports() {
        assert_eq!(
            serde_json::from_str::<Port>("22").unwrap(),
            Port::SSH_DEFAULT
        );
        assert_eq!(
            serde_json::from_str::<Port>("\"2222\"").unwrap().get(),
            2222
        );
    }

    #[test]
    fn rejects_invalid_ports() {
        for value in ["0", "65536", "-1", "\"ssh\"", "null"] {
            assert!(
                serde_json::from_str::<Port>(value).is_err(),
                "accepted {value}"
            );
        }
    }
}
