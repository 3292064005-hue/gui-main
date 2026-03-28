import zmq
import threading
from .ipc_messages import unpack_robot_telemetry, SIZE_ROBOT_TELEMETRY

class ZeroCopyIpcClient:
    """
    A dedicated background thread mapping binary IPC Streams from C++ 'cpp_robot_core'
    directly into our Zero-GC 'PreAllocatedRingBuffer'.
    It bypasses all Python string/JSON/dict allocators for max stability under 1kHz load.
    """
    def __init__(self, memory_pool, address="tcp://127.0.0.1:5555"):
        self.memory_pool = memory_pool
        self.address = address
        self.context = zmq.Context()
        self.socket = self.context.socket(zmq.SUB)
        # Fast configuration
        self.socket.setsockopt(zmq.RCVHWM, 2000) # Keep 2 sec buffer if stuttering
        self.socket.setsockopt_string(zmq.SUBSCRIBE, "") # All topics
        
        self.is_running = False
        self._thread = None

    def start(self):
        self.socket.connect(self.address)
        self.is_running = True
        self._thread = threading.Thread(target=self._recv_loop, daemon=True)
        self._thread.start()

    def _recv_loop(self):
        while self.is_running:
            try:
                # recv(copy=False) returns a zero-copy memoryview zmq.Frame
                packet = self.socket.recv(copy=False)
                
                # Verify exactly sized C-Struct POD packet
                if len(packet) == SIZE_ROBOT_TELEMETRY:
                    # Native high-speed un-packing directly against memoryview
                    raw_data = unpack_robot_telemetry(packet.buffer)
                    # Feed right into the RingBuffer mapping
                    self.memory_pool.write_frame_zero_copy(raw_data)
                    
            except zmq.ZMQError as e:
                pass # Non-blocking loop
            except Exception as e:
                print(f"IPC Error: {e}")

    def stop(self):
        self.is_running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        self.socket.close()
        self.context.term()
