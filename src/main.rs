use std::{error::Error, net::SocketAddr};

use tokio::net::TcpListener;
use webssh::{config::Config, server};

#[tokio::main]
async fn main() -> Result<(), Box<dyn Error>> {
    let config = Config::from_env()?;
    let address = SocketAddr::from(([0, 0, 0, 0], config.port().get()));
    let listener = TcpListener::bind(address).await?;

    println!("Starting server on port {}", config.port());
    axum::serve(
        listener,
        server::router().into_make_service_with_connect_info::<SocketAddr>(),
    )
    .await?;
    Ok(())
}
