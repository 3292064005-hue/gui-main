from __future__ import annotations

import os
import socket
import ssl
import struct
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TLS_CERT = REPO_ROOT / "configs" / "tls" / "runtime" / "robot_core_server.crt"
FALLBACK_TLS_CERT = REPO_ROOT / "configs" / "tls" / "robot_core_server.crt"
DEFAULT_TLS_KEY = REPO_ROOT / "configs" / "tls" / "runtime" / "robot_core_server.key"
DEFAULT_TLS_SERVER_NAME = os.getenv("ROBOT_CORE_TLS_SERVER_NAME", "localhost")
MAX_FRAME_BYTES = 4 * 1024 * 1024


def resolve_tls_cert_path() -> Path:
    """Resolve the trust anchor used by the runtime TLS client.

    Returns:
        Absolute certificate path.

    Raises:
        No exceptions are raised directly. Environment overrides are resolved as-is.
    """
    env_value = os.getenv("ROBOT_CORE_TLS_CERT")
    if env_value:
        return Path(env_value).expanduser().resolve()
    return DEFAULT_TLS_CERT if DEFAULT_TLS_CERT.exists() else FALLBACK_TLS_CERT


def resolve_tls_key_path() -> Path:
    """Resolve the TLS private key path for server-side runtime transport.

    Returns:
        Absolute key path.

    Raises:
        No exceptions are raised directly. Missing files are handled by SSL context creation.
    """
    env_value = os.getenv("ROBOT_CORE_TLS_KEY")
    if env_value:
        return Path(env_value).expanduser().resolve()
    return DEFAULT_TLS_KEY


def create_client_ssl_context(cert_path: Path | None = None) -> ssl.SSLContext:
    """Create a TLS 1.3 client context for robot_core transports.

    Args:
        cert_path: Optional trust anchor override.

    Returns:
        Configured TLS client context.

    Raises:
        FileNotFoundError: If the resolved CA file does not exist.
        ssl.SSLError: If the trust material cannot be loaded.
    """
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
    """Create a TLS 1.3 server context for robot_core transports.

    Args:
        cert_path: Optional certificate override.
        key_path: Optional private-key override.

    Returns:
        Configured TLS server context.

    Raises:
        FileNotFoundError: If the resolved certificate or key is missing.
        ssl.SSLError: If the certificate chain cannot be loaded.
    """
    cert_file = cert_path or resolve_tls_cert_path()
    key_file = key_path or resolve_tls_key_path()
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_3
    context.maximum_version = ssl.TLSVersion.TLSv1_3
    context.load_cert_chain(certfile=str(cert_file), keyfile=str(key_file))
    return context


def send_length_prefixed_message(sock: socket.socket, payload: bytes) -> None:
    """Send a single length-prefixed frame.

    Args:
        sock: Connected TCP/TLS socket.
        payload: Serialized protobuf frame.

    Returns:
        None.

    Raises:
        OSError: If the socket write fails.
        ValueError: If the payload exceeds the frame limit.
    """
    if len(payload) > MAX_FRAME_BYTES:
        raise ValueError(f"protobuf frame exceeds limit: {len(payload)} > {MAX_FRAME_BYTES}")
    sock.sendall(struct.pack("!I", len(payload)))
    sock.sendall(payload)


def recv_exact(sock: socket.socket, size: int) -> bytes:
    """Read an exact number of bytes from the socket.

    Args:
        sock: Connected TCP/TLS socket.
        size: Required byte count.

    Returns:
        Byte string with exactly ``size`` bytes.

    Raises:
        ValueError: If ``size`` is negative.
        ConnectionError: If the peer closes the connection early.
        OSError: If the socket read fails.
    """
    if size < 0:
        raise ValueError("recv_exact size must be non-negative")
    chunks = bytearray()
    while len(chunks) < size:
        chunk = sock.recv(size - len(chunks))
        if not chunk:
            raise ConnectionError("connection closed while receiving protobuf frame")
        chunks.extend(chunk)
    return bytes(chunks)


def recv_length_prefixed_message(sock: socket.socket) -> bytes:
    """Receive a single length-prefixed protobuf frame.

    Args:
        sock: Connected TCP/TLS socket.

    Returns:
        Serialized protobuf payload.

    Raises:
        ValueError: If the decoded frame length is invalid.
        ConnectionError: If the peer closes the connection early.
        OSError: If the socket read fails.
    """
    header = recv_exact(sock, 4)
    (length,) = struct.unpack("!I", header)
    if length <= 0 or length > MAX_FRAME_BYTES:
        raise ValueError(f"invalid protobuf frame length: {length}")
    return recv_exact(sock, length)
