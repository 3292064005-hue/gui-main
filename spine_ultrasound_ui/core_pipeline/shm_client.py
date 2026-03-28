import ctypes
import time
import atexit
from multiprocessing import shared_memory
import numpy as np

# 1. 精确映射 C++ 的内存布局 (严禁修改字段顺序和类型)
class PoseData(ctypes.Structure):
    _fields_ = [
        ("timestamp_ns", ctypes.c_uint64),
        ("position", ctypes.c_double * 3),
        ("orientation", ctypes.c_double * 4),
        ("external_torques", ctypes.c_double * 6)
    ]

class SeqlockPoseRecord(ctypes.Structure):
    _fields_ = [
        ("sequence", ctypes.c_uint32),
        ("_padding", ctypes.c_uint32), # 严格对应 C++ 的 8字节对齐
        ("data", PoseData)
    ]

RING_BUFFER_SIZE = 4096

class ShmLayout(ctypes.Structure):
    _fields_ = [
        ("head", ctypes.c_uint32),
        ("_padding", ctypes.c_uint32), # 严格对应
        ("records", SeqlockPoseRecord * RING_BUFFER_SIZE)
    ]

class ShmPoseReader:
    def __init__(self, shm_name="/spine_pose_shm"):
        self.shm_name = shm_name.lstrip('/') # Linux 下 shared_memory 模块通常不需要前导斜杠
        self.shm = None
        self.layout = None

        # 挂载清理钩子，应对 Python 异常退出
        atexit.register(self.close)
        self._connect()

    def _connect(self):
        """尝试连接到 C++ 创建的共享内存"""
        try:
            self.shm = shared_memory.SharedMemory(name=self.shm_name, create=False)
            # 【最优解】将共享内存的 buffer 直接强转为 ctypes 结构体，真正的零拷贝
            self.layout = ShmLayout.from_buffer(self.shm.buf)
            print(f"[IPC Python] Successfully connected to SHM: {self.shm_name}")
        except FileNotFoundError:
            raise RuntimeError(f"SHM {self.shm_name} not found. Is C++ core running?")

    def get_latest_pose(self):
        """
        获取最新一帧的机器位姿。
        采用 Seqlock 无锁自旋机制，保证读取时数据不会被 C++ 覆盖破坏。
        """
        if not self.layout:
            return None

        # 读取当前的头指针
        head_idx = self.layout.head
        target_record = self.layout.records[head_idx]

        # Seqlock 自旋读取机制
        while True:
            seq1 = target_record.sequence

            # 如果是奇数，说明 C++ 正在写入，自旋等待
            if seq1 % 2 != 0:
                continue

            # 拷贝数据 (在 C++ 没有写入的时间窗口内)
            ts = target_record.data.timestamp_ns
            pos = np.array(target_record.data.position, dtype=np.float64)
            ori = np.array(target_record.data.orientation, dtype=np.float64)
            torques = np.array(target_record.data.external_torques, dtype=np.float64)

            seq2 = target_record.sequence

            # 如果读取前后序列号一致，说明读取期间数据未被破坏，读取成功
            if seq1 == seq2:
                return ts, pos, ori, torques
            # 否则，数据已被新一轮循环覆盖，自动进行下一轮自旋重试

    def close(self):
        """安全释放资源"""
        if self.shm:
            self.shm.close() # 注意：Python 作为 Client 只 close，不 unlink，留给 C++ 销毁
            self.shm = None
            print("[IPC Python] SHM disconnected.")

# 使用示例 (在独立进程 data_acquisition_proc.py 中调用)
if __name__ == "__main__":
    try:
        reader = ShmPoseReader("spine_pose_shm")
        # 模拟高频读取
        for _ in range(100):
            ts, pos, ori, force = reader.get_latest_pose()
            print(f"Read at TS {ts}: Z-Force = {force[2]:.2f}N")
            time.sleep(0.01)
    except Exception as e:
        print(e)