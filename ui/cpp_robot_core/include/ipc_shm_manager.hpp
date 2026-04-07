#pragma once

#include <atomic>
#include <cstdint>
#include <cstring>
#include <stdexcept>
#include <iostream>
#include <fcntl.h>
#include <sys/mman.h>
#include <unistd.h>

// 1. 基础数据载体 (保持纯粹的 POD 类型)
struct PoseData {
    uint64_t timestamp_ns;
    double position[3];
    double orientation[4]; // w, x, y, z
    double external_torques[6];
};

// 2. 顺序锁记录块 (解决跨进程读写冲突)
struct SeqlockPoseRecord {
    std::atomic<uint32_t> sequence{0};
    uint32_t _padding{0}; // 【核心细节】强制内存对齐，填补到8字节边界，防止跨语言解析错位！
    PoseData data;
};

// 3. 共享内存整体布局
constexpr size_t RING_BUFFER_SIZE = 4096;
struct ShmLayout {
    std::atomic<uint32_t> head{0};
    uint32_t _padding{0}; // 强制内存对齐
    SeqlockPoseRecord records[RING_BUFFER_SIZE];
};

class IPCSharedMemoryManager {
private:
    const char* shm_name_;
    int shm_fd_{-1};
    ShmLayout* shm_ptr_{nullptr};

public:
    IPCSharedMemoryManager(const char* name) : shm_name_(name) {
        // 【核心防御】启动前强制 Unlink，防备上一次进程崩溃导致的僵尸内存残留
        shm_unlink(shm_name_);

        // 创建并独占共享内存
        shm_fd_ = shm_open(shm_name_, O_CREAT | O_RDWR | O_EXCL, 0666);
        if (shm_fd_ == -1) {
            throw std::runtime_error("Failed to create shared memory.");
        }

        // 调整内存大小
        if (ftruncate(shm_fd_, sizeof(ShmLayout)) == -1) {
            throw std::runtime_error("Failed to set shared memory size.");
        }

        // 映射到当前进程的虚拟地址空间
        void* mapped = mmap(nullptr, sizeof(ShmLayout), PROT_READ | PROT_WRITE, MAP_SHARED, shm_fd_, 0);
        if (mapped == MAP_FAILED) {
            throw std::runtime_error("Failed to mmap shared memory.");
        }

        shm_ptr_ = new (mapped) ShmLayout(); // Placement new，初始化原子变量
        std::cout << "[IPC C++] SHM Initialized. Zero-copy Ready. Name: " << shm_name_ << "\n";
    }

    ~IPCSharedMemoryManager() {
        if (shm_ptr_) munmap(shm_ptr_, sizeof(ShmLayout));
        if (shm_fd_ != -1) close(shm_fd_);
        shm_unlink(shm_name_); // 正常退出时销毁
    }

    // 高频非阻塞写入 (1kHz 调用)
    void publish_pose(const PoseData& new_data) {
        if (!shm_ptr_) return;

        // 获取下一个写入位置
        uint32_t current_head = shm_ptr_->head.load(std::memory_order_relaxed);
        uint32_t next_head = (current_head + 1) % RING_BUFFER_SIZE;
        SeqlockPoseRecord& record = shm_ptr_->records[next_head];

        // Seqlock 第一步：获取当前序列号，变奇数表示"正在写入"
        uint32_t seq = record.sequence.load(std::memory_order_relaxed);
        record.sequence.store(seq + 1, std::memory_order_release); // Release屏障，保证后续写入不被重排到上面

        // 零拷贝写入数据
        std::memcpy(&record.data, &new_data, sizeof(PoseData));

        // Seqlock 第二步：序列号变偶数表示"写入完成"
        record.sequence.store(seq + 2, std::memory_order_release);

        // 更新全局环形队列头指针
        shm_ptr_->head.store(next_head, std::memory_order_release);
    }
};