#ifndef SPSC_QUEUE_HPP
#define SPSC_QUEUE_HPP

#include <atomic>
#include <vector>
#include <cstddef>
#include <cassert>

namespace spine_core {

// Single-Producer Single-Consumer Lock-Free Ring Buffer
// Designed strictly for 1ms hard real-time latency with zero allocations.
template<typename T>
class SPSCQueue {
public:
    explicit SPSCQueue(size_t capacity)
        : capacity_(capacity), head_(0), tail_(0) {
        // Add +1 to distinguish full from empty
        buffer_.resize(capacity_ + 1);
    }

    // Producer only: push to queue
    bool try_enqueue(const T& item) {
        size_t current_tail = tail_.load(std::memory_order_relaxed);
        size_t next_tail = (current_tail + 1) % buffer_.size();
        
        if (next_tail == head_.load(std::memory_order_acquire)) {
            return false; // Queue is full
        }
        
        buffer_[current_tail] = item;
        tail_.store(next_tail, std::memory_order_release);
        return true;
    }

    // Consumer only: pop from queue
    bool try_dequeue(T& item) {
        size_t current_head = head_.load(std::memory_order_relaxed);
        
        if (current_head == tail_.load(std::memory_order_acquire)) {
            return false; // Queue is empty
        }
        
        item = buffer_[current_head];
        head_.store((current_head + 1) % buffer_.size(), std::memory_order_release);
        return true;
    }
    
    // Clear the queue (called from consumer or when stopped)
    void clear() {
        T dummy;
        while(try_dequeue(dummy)) {}
    }

private:
    std::vector<T> buffer_;
    size_t capacity_;
    alignas(64) std::atomic<size_t> head_; // Padding to prevent false sharing
    alignas(64) std::atomic<size_t> tail_;
};

} // namespace spine_core

#endif // SPSC_QUEUE_HPP
