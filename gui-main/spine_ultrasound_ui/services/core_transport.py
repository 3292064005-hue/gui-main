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


def parse_reply_payload(payload_bytes: bytes) -> ReplyEnvelope:
    from . import ipc_messages_pb2

    proto = ipc_messages_pb2.Reply()
    proto.ParseFromString(payload_bytes)
    reply = ReplyEnvelope.from_protobuf(proto)
    ensure_protocol_version(reply.protocol_version, "Reply")
    return reply


def parse_telemetry_payload(payload_bytes: bytes) -> TelemetryEnvelope:
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
    connect_timeout_s: float = 1.5,
    read_timeout_s: float = 2.0,
) -> ReplyEnvelope:
    env = CommandEnvelope(command=command, payload=payload or {}, request_id=request_id or uuid.uuid4().hex)
    with socket.create_connection((command_host, command_port), timeout=connect_timeout_s) as raw_sock:
        raw_sock.settimeout(read_timeout_s)
        with ssl_context.wrap_socket(raw_sock, server_hostname=DEFAULT_TLS_SERVER_NAME) as tls_sock:
            send_length_prefixed_message(tls_sock, env.to_protobuf().SerializeToString())
            payload_bytes = recv_length_prefixed_message(tls_sock)
    return parse_reply_payload(payload_bytes)
