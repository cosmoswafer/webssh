use std::{collections::VecDeque, net::SocketAddr};

use axum::{
    extract::{
        ws::{Message, WebSocket},
        ConnectInfo, WebSocketUpgrade,
    },
    response::IntoResponse,
    routing::get,
    Router,
};
use futures_util::{
    stream::{SplitSink, SplitStream},
    SinkExt, StreamExt,
};
use tower_http::services::{ServeDir, ServeFile};

use crate::{
    protocol::{parse_client_message, parse_connect_request, ClientMessage},
    ssh::{SshError, SshEvent, SshSession},
};

pub fn router() -> Router {
    Router::new()
        .route_service("/", ServeFile::new("index.html"))
        .route("/connect", get(websocket_handler))
        .nest_service("/static", ServeDir::new("static"))
}

async fn websocket_handler(
    ws: WebSocketUpgrade,
    ConnectInfo(peer): ConnectInfo<SocketAddr>,
) -> impl IntoResponse {
    ws.on_upgrade(move |socket| handle_socket(socket, peer))
}

async fn handle_socket(socket: WebSocket, peer: SocketAddr) {
    eprintln!("New connection from {peer}");
    if let Err(error) = run_socket(socket).await {
        eprintln!("Connection error from {peer}: {error}");
    }
    eprintln!("Connection closed from {peer}");
}

async fn run_socket(socket: WebSocket) -> Result<(), SocketError> {
    let (mut socket_sender, mut socket_receiver) = socket.split();

    let request = loop {
        match socket_receiver.next().await {
            Some(Ok(Message::Text(text))) => {
                break match parse_connect_request(&text) {
                    Ok(request) => request,
                    Err(error) => {
                        send_terminal(
                            &mut socket_sender,
                            format!("Failed to connect: {error}\r\n"),
                        )
                        .await?;
                        return Ok(());
                    }
                };
            }
            Some(Ok(Message::Close(_))) | None => return Ok(()),
            Some(Ok(Message::Ping(_) | Message::Pong(_) | Message::Binary(_))) => {}
            Some(Err(error)) => return Err(SocketError::WebSocket(error.to_string())),
        }
    };

    let mut pending_messages = VecDeque::new();
    let connecting = SshSession::connect(request);
    tokio::pin!(connecting);

    let session = loop {
        tokio::select! {
            result = &mut connecting => {
                break match result {
                    Ok(session) => session,
                    Err(error) => {
                        send_terminal(
                            &mut socket_sender,
                            format!("Failed to connect: {error}\r\n"),
                        )
                        .await?;
                        return Ok(());
                    }
                };
            }
            socket_message = socket_receiver.next() => {
                match socket_message {
                    Some(Ok(message @ (Message::Text(_) | Message::Binary(_)))) => {
                        if pending_messages.len() == 64 {
                            return Err(SocketError::WebSocket(
                                "too much terminal input received during SSH connection".into(),
                            ));
                        }
                        pending_messages.push_back(message);
                    }
                    Some(Ok(Message::Ping(_) | Message::Pong(_))) => {}
                    Some(Ok(Message::Close(_))) | None => return Ok(()),
                    Some(Err(error)) => {
                        return Err(SocketError::WebSocket(error.to_string()));
                    }
                }
            }
        }
    };

    send_terminal(&mut socket_sender, "Connected to SSH server\r\n").await?;
    relay_connection(session, socket_sender, socket_receiver, pending_messages).await
}

async fn relay_connection(
    session: SshSession,
    mut socket_sender: SplitSink<WebSocket, Message>,
    socket_receiver: SplitStream<WebSocket>,
    pending_messages: VecDeque<Message>,
) -> Result<(), SocketError> {
    let (ssh_sender, mut ssh_events) = session.split();
    let pending =
        futures_util::stream::iter(pending_messages.into_iter().map(Ok::<Message, axum::Error>));
    let mut socket_receiver = pending.chain(socket_receiver);

    loop {
        tokio::select! {
            socket_message = socket_receiver.next() => {
                match socket_message {
                    Some(Ok(Message::Text(text))) => {
                        match parse_client_message(text.to_string()) {
                            Ok(ClientMessage::Input(input)) => {
                                ssh_sender.send_input(input).await?;
                            }
                            Ok(ClientMessage::Resize(resize)) => {
                                ssh_sender.resize(resize).await?;
                            }
                            Err(error) => {
                                send_terminal(
                                    &mut socket_sender,
                                    format!("\r\nInvalid message: {error}\r\n"),
                                ).await?;
                            }
                        }
                    }
                    Some(Ok(Message::Binary(data))) => {
                        ssh_sender
                            .send_input(String::from_utf8_lossy(&data).into_owned())
                            .await?;
                    }
                    Some(Ok(Message::Ping(_) | Message::Pong(_))) => {}
                    Some(Ok(Message::Close(_))) | None => return Ok(()),
                    Some(Err(error)) => {
                        return Err(SocketError::WebSocket(error.to_string()));
                    }
                }
            }
            output = ssh_events.recv() => {
                match output {
                    Some(SshEvent::Output(output)) => {
                        send_terminal(&mut socket_sender, output).await?;
                    }
                    Some(SshEvent::Error(error)) => {
                        send_terminal(
                            &mut socket_sender,
                            format!("\r\nSSH error: {error}\r\n"),
                        ).await?;
                    }
                    Some(SshEvent::Closed) | None => return Ok(()),
                }
            }
        }
    }
}

async fn send_terminal(
    sender: &mut SplitSink<WebSocket, Message>,
    text: impl Into<String>,
) -> Result<(), SocketError> {
    sender
        .send(Message::Text(text.into().into()))
        .await
        .map_err(|error| SocketError::WebSocket(error.to_string()))
}

#[derive(Debug, thiserror::Error)]
enum SocketError {
    #[error("{0}")]
    Ssh(#[from] SshError),
    #[error("WebSocket error: {0}")]
    WebSocket(String),
}

#[cfg(test)]
mod tests {
    use axum::{
        body::Body,
        http::{Request, StatusCode},
    };
    use http_body_util::BodyExt;
    use tower::ServiceExt;

    use super::*;

    #[tokio::test]
    async fn serves_index_and_javascript_from_repo_files() {
        let app = router();

        let index = app
            .clone()
            .oneshot(Request::builder().uri("/").body(Body::empty()).unwrap())
            .await
            .unwrap();
        assert_eq!(index.status(), StatusCode::OK);
        assert!(index.headers()["content-type"]
            .to_str()
            .unwrap()
            .starts_with("text/html"));
        let index_body = index.into_body().collect().await.unwrap().to_bytes();
        assert_eq!(index_body.as_ref(), include_bytes!("../index.html"));

        let javascript = app
            .oneshot(
                Request::builder()
                    .uri("/static/js/app.js")
                    .body(Body::empty())
                    .unwrap(),
            )
            .await
            .unwrap();
        assert_eq!(javascript.status(), StatusCode::OK);
        let script_body = javascript.into_body().collect().await.unwrap().to_bytes();
        assert_eq!(script_body.as_ref(), include_bytes!("../static/js/app.js"));
    }
}
