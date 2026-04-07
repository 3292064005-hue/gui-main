from __future__ import annotations

import socket
import ssl
import uuid
from typing import Optional

from .ipc_protocol import CommandEnvelope, ReplyEnvelope, TelemetryEnvelope, ensure_protocol_version
from .protobuf_transport import (
    DEFAULT_TLS_SERVER_NAME,
    recv_length_prefixed_message,
    send_length_prefixed_message,
)

DEFAULT_COMMAND_CONNECT_TIMEOUT_S = 1.5
DEFAULT_COMMAND_READ_TIMEOUT_S = 2.0


def parse_reply_payload(payload_bytes: bytes) -> ReplyEnvelope:
    """Deserialize a reply frame from protobuf.

    Args:
        payload_bytes: Serialized protobuf reply bytes.

    Returns:
        Parsed reply envelope.

    Raises:
        ValueError: If protocol-version validation fails.
        Exception: Protobuf parsing exceptions are propagated by the generated binding.
    """
    from . import ipc_messages_pb2

    proto = ipc_messages_pb2.Reply()
    proto.ParseFromString(payload_bytes)
    reply = ReplyEnvelope.from_protobuf(proto)
    ensure_protocol_version(reply.protocol_version, "Reply")
    return reply


def parse_telemetry_payload(payload_bytes: bytes) -> TelemetryEnvelope:
    """Deserialize a telemetry frame from protobuf.

    Args:
        payload_bytes: Serialized protobuf telemetry bytes.

    Returns:
        Parsed telemetry envelope.

    Raises:
        ValueError: If protocol-version validation fails.
        Exception: Protobuf parsing exceptions are propagated by the generated binding.
    """
    from . import ipc_messages_pb2

    proto = ipc_messages_pb2.TelemetryEnvelope()
    proto.ParseFromString(payload_bytes)
    env = TelemetryEnvelope.from_protobuf(proto)
    ensure_protocol_version(env.protocol_version, "TelemetryEnvelope")
    return env


def send_tls_command(
    command_host: str,
    command_port: int,
    ssl_context: ssl.SSLContext,
    command: str,
    payload: Optional[dict] = None,
    *,
    request_id: str | None = None,
    connect_timeout_s: float = DEFAULT_COMMAND_CONNECT_TIMEOUT_S,
    read_timeout_s: float = DEFAULT_COMMAND_READ_TIMEOUT_S,
) -> ReplyEnvelope:
    """Send one command over the TLS protobuf transport.

    Args:
        command_host: Runtime command host.
        command_port: Runtime command port.
        ssl_context: Configured TLS context.
        command: Canonical command name.
        payload: Optional command payload.
        request_id: Optional explicit request id.
        connect_timeout_s: TCP connect timeout in seconds.
        read_timeout_s: Reply read timeout in seconds.

    Returns:
        Parsed reply envelope.

    Raises:
        ValueError: If command is empty or timeouts are non-positive.
        OSError: If the TCP/TLS transport fails.
        ssl.SSLError: If the TLS handshake fails.
    """
    if not str(command).strip():
        raise ValueError("command must be non-empty")
    if connect_timeout_s <= 0 or read_timeout_s <= 0:
        raise ValueError("connect_timeout_s and read_timeout_s must be positive")
    env = CommandEnvelope(command=command, payload=payload or {}, request_id=request_id or uuid.uuid4().hex)
    with socket.create_connection((command_host, command_port), timeout=connect_timeout_s) as raw_sock:
        raw_sock.settimeout(read_timeout_s)
        raw_sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        with ssl_context.wrap_socket(raw_sock, server_hostname=DEFAULT_TLS_SERVER_NAME) as tls_sock:
            send_length_prefixed_message(tls_sock, env.to_protobuf().SerializeToString())
            payload_bytes = recv_length_prefixed_message(tls_sock)
    return parse_reply_payload(payload_bytes)
