from __future__ import annotations

import threading
import zmq
from loguru import logger

from .ipc_messages import SIZE_ROBOT_TELEMETRY, unpack_robot_telemetry


class ZeroCopyIpcClient:
    """Background subscriber that maps binary telemetry packets into the ring buffer."""

    def __init__(self, memory_pool, address="tcp://127.0.0.1:5555"):
        self.memory_pool = memory_pool
        self.address = address
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        self.socket.setsockopt(zmq.RCVHWM, 2000)
        self.socket.setsockopt_string(zmq.SUBSCRIBE, "")
        self.is_running = False
        self._thread = None

    def start(self):
        self.socket.connect(self.address)
        self.is_running = True
        self._thread = threading.Thread(target=self._recv_loop, daemon=True, name="zero-copy-ipc")
        self._thread.start()

    def _recv_loop(self):
        while self.is_running:
            try:
                packet = self.socket.recv(copy=False)
                if len(packet) == SIZE_ROBOT_TELEMETRY:
                    raw_data = unpack_robot_telemetry(packet.buffer)
                    self.memory_pool.write_frame_zero_copy(raw_data)
                else:
                    logger.warning("IPC packet size mismatch: expected {} bytes, got {}", SIZE_ROBOT_TELEMETRY, len(packet))
            except zmq.ZMQError as exc:
                if self.is_running:
                    logger.debug("IPC recv loop waiting for telemetry: {}", exc)
            except Exception as exc:  # pragma: no cover - runtime safety net
                logger.exception("IPC error while decoding telemetry: {}", exc)

    def stop(self):
        self.is_running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        self.socket.close()
        self.context.term()
