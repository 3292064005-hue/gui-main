import ctypes
import time
import atexit
from multiprocessing import shared_memory
import numpy as np
from scipy.spatial.transform import Slerp
from scipy.spatial.transform import Rotation as R

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
        self._closed = False

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

    def query_interpolated_pose(self, target_ts_ns):
        """
        最优解：根据图像的硬件时间戳，在 4096 个历史记录中二分查找并插值
         target_ts_ns: 图像产生时的纳秒时间戳
        """
        if not self.layout:
            return None

        # 1. 获取当前头尾状态 (无锁读取当前快照)
        head_idx = self.layout.head

        # 为了避免读取耗时导致数据被 C++ 覆盖，我们先将相关的元数据拷贝出来
        # 实际工业级做法是在 4096 长度中，最近 1-2 秒的数据是绝对安全的

        # 寻找紧邻 target_ts_ns 的前后两帧 t1 和 t2
        # (由于环形队列是按时间顺序写入的，可以从 head 开始往回找)

        idx = head_idx
        record_t2 = None
        record_t1 = None

        # 往回搜索最多 2000 帧 (即 2 秒内的延迟)
        for _ in range(2000):
            idx = (idx - 1) % RING_BUFFER_SIZE
            seq1 = self.layout.records[idx].sequence
            if seq1 % 2 != 0:
                continue # 跳过正在写入的脏数据

            current_ts = self.layout.records[idx].data.timestamp_ns

            if current_ts >= target_ts_ns:
                record_t2 = self.layout.records[idx].data
            elif current_ts < target_ts_ns:
                record_t1 = self.layout.records[idx].data
                break # 找到了夹逼的区间 [t1, target, t2]

        if record_t1 is None or record_t2 is None:
            # 延迟太大或者时间戳异常，找不到历史记录
            return None

        # 2. 提取数据
        t1, t2 = record_t1.timestamp_ns, record_t2.timestamp_ns

        # 如果时间差极小，直接返回最近的
        if t2 - t1 == 0:
            return np.array(record_t1.position), np.array(record_t1.orientation)

        # 3. 计算插值系数 alpha (0.0 到 1.0 之间)
        alpha = (target_ts_ns - t1) / (t2 - t1)

        # 4. 线性插值 (Lerp) -> 处理位置 xyz
        pos1 = np.array(record_t1.position)
        pos2 = np.array(record_t2.position)
        interpolated_pos = pos1 + alpha * (pos2 - pos1)

        # 5. 球面线性插值 (Slerp) -> 处理四元数旋转
        # 注意: scipy 的 Rotation 默认四元数格式为 [x, y, z, w]
        # 需确认你的 C++ 核心发来的四元数顺序是否匹配，此处假设 C++ 发的是 w,x,y,z
        quat1 = [record_t1.orientation[1], record_t1.orientation[2], record_t1.orientation[3], record_t1.orientation[0]]
        quat2 = [record_t2.orientation[1], record_t2.orientation[2], record_t2.orientation[3], record_t2.orientation[0]]

        try:
            key_times = [0, 1]
            key_rots = R.from_quat([quat1, quat2])
            slerp = Slerp(key_times, key_rots)
            interpolated_rot = slerp([alpha])[0] # 取出时间为 alpha 的旋转

            # 转回 [w, x, y, z] 输出
            res_q = interpolated_rot.as_quat()
            final_quat = np.array([res_q[3], res_q[0], res_q[1], res_q[2]])

        except Exception:
            # Slerp 退化保护：如果两帧旋转极度接近导致计算奇异，退化为取 t1
            final_quat = np.array(record_t1.orientation)

        return interpolated_pos, final_quat

    def close(self):
        """安全释放资源"""
        if self._closed:
            return
        self._closed = True

        atexit.unregister(self.close)

        if self.layout is not None:
            # `from_buffer()` keeps an exported pointer alive until the ctypes
            # wrapper is released, so drop it before closing the mmap.
            self.layout = None

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
