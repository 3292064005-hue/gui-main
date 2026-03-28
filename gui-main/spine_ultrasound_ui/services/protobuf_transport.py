from __future__ import annotations

import os
import socket
import ssl
import struct
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TLS_CERT = REPO_ROOT / "configs" / "tls" / "robot_core_server.crt"
DEFAULT_TLS_KEY = REPO_ROOT / "configs" / "tls" / "robot_core_server.key"
DEFAULT_TLS_SERVER_NAME = os.getenv("ROBOT_CORE_TLS_SERVER_NAME", "localhost")


def resolve_tls_cert_path() -> Path:
    env_value = os.getenv("ROBOT_CORE_TLS_CERT")
    if env_value:
        return Path(env_value).expanduser().resolve()
    return DEFAULT_TLS_CERT


def resolve_tls_key_path() -> Path:
    env_value = os.getenv("ROBOT_CORE_TLS_KEY")
    if env_value:
        return Path(env_value).expanduser().resolve()
    return DEFAULT_TLS_KEY


def create_client_ssl_context(cert_path: Path | None = None) -> ssl.SSLContext:
    trust_anchor = cert_path or resolve_tls_cert_path()
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.minimum_version = ssl.TLSVersion.TLSv1_3
    context.maximum_version = ssl.TLSVersion.TLSv1_3
    context.check_hostname = False
    context.verify_mode = ssl.CERT_REQUIRED
    context.load_verify_locations(cafile=str(trust_anchor))
    return context


def create_server_ssl_context(
    cert_path: Path | None = None,
    key_path: Path | None = None,
) -> ssl.SSLContext:
    cert_file = cert_path or resolve_tls_cert_path()
    key_file = key_path or resolve_tls_key_path()
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_3
    context.maximum_version = ssl.TLSVersion.TLSv1_3
    context.load_cert_chain(certfile=str(cert_file), keyfile=str(key_file))
    return context


def send_length_prefixed_message(sock: socket.socket, payload: bytes) -> None:
    sock.sendall(struct.pack("!I", len(payload)))
    sock.sendall(payload)


def recv_exact(sock: socket.socket, size: int) -> bytes:
    chunks = bytearray()
    while len(chunks) < size:
        chunk = sock.recv(size - len(chunks))
        if not chunk:
            raise ConnectionError("connection closed while receiving protobuf frame")
        chunks.extend(chunk)
    return bytes(chunks)


def recv_length_prefixed_message(sock: socket.socket) -> bytes:
    header = recv_exact(sock, 4)
    (length,) = struct.unpack("!I", header)
    return recv_exact(sock, length)
