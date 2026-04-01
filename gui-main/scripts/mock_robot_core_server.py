#!/usr/bin/env python3
from __future__ import annotations

import socket
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from spine_ultrasound_ui.services import ipc_messages_pb2
from spine_ultrasound_ui.services.ipc_protocol import CommandEnvelope, PROTOCOL_VERSION, ReplyEnvelope
from spine_ultrasound_ui.services.mock_core_runtime import MockCoreRuntime
from spine_ultrasound_ui.services.protobuf_transport import (
    create_server_ssl_context,
    recv_length_prefixed_message,
    send_length_prefixed_message,
)

HOST = "127.0.0.1"
COMMAND_PORT = 5656
TELEMETRY_PORT = 5657

runtime = MockCoreRuntime()
telemetry_clients: list[socket.socket] = []
lock = threading.Lock()
ssl_context = create_server_ssl_context()


def send_reply(sock: socket.socket, proto_msg) -> None:
    send_length_prefixed_message(sock, proto_msg.SerializeToString())


def close_client(conn: socket.socket) -> None:
    try:
        conn.shutdown(socket.SHUT_RDWR)
    except OSError:
        pass
    conn.close()


def handle_command(conn: socket.socket) -> None:
    with conn:
        while True:
            try:
                payload = recv_length_prefixed_message(conn)
            except ConnectionError:
                return
            req_proto = ipc_messages_pb2.Command()
            req_proto.ParseFromString(payload)
            req = CommandEnvelope.from_protobuf(req_proto)
            if req.protocol_version != PROTOCOL_VERSION:
                send_reply(
                    conn,
                    ReplyEnvelope(
                        ok=False,
                        message="protocol version mismatch",
                        request_id=req.request_id,
                        data={},
                    ).to_protobuf(),
                )
                return
            with lock:
                reply = runtime.handle_command(req.command, req.payload)
                reply.request_id = req.request_id
                snapshot = runtime.telemetry_snapshot()
            send_reply(conn, reply.to_protobuf())
            broadcast(snapshot)


def command_server() -> None:
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, COMMAND_PORT))
    srv.listen()
    print(f"[mock_robot_core] command server on {HOST}:{COMMAND_PORT} (TLS/Protobuf)")
    while True:
        conn, _ = srv.accept()
        tls_conn = ssl_context.wrap_socket(conn, server_side=True)
        threading.Thread(target=handle_command, args=(tls_conn,), daemon=True).start()


def telemetry_server() -> None:
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, TELEMETRY_PORT))
    srv.listen()
    print(f"[mock_robot_core] telemetry server on {HOST}:{TELEMETRY_PORT} (TLS/Protobuf)")
    while True:
        conn, _ = srv.accept()
        tls_conn = ssl_context.wrap_socket(conn, server_side=True)
        with lock:
            telemetry_clients.append(tls_conn)
            snapshot = runtime.telemetry_snapshot()
        print("[mock_robot_core] telemetry client connected")
        broadcast(snapshot)


def broadcast(messages) -> None:
    dead: list[socket.socket] = []
    encoded = [env.to_protobuf().SerializeToString() for env in messages]
    with lock:
        for client in telemetry_clients:
            try:
                for payload in encoded:
                    send_length_prefixed_message(client, payload)
            except OSError:
                dead.append(client)
        for client in dead:
            telemetry_clients.remove(client)
            close_client(client)


def telemetry_loop() -> None:
    while True:
        time.sleep(0.1)
        with lock:
            messages = runtime.tick()
        broadcast(messages)


if __name__ == "__main__":
    threading.Thread(target=command_server, daemon=True).start()
    threading.Thread(target=telemetry_server, daemon=True).start()
    telemetry_loop()
