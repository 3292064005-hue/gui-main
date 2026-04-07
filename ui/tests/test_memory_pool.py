from spine_ultrasound_ui.core.memory_pool import PreAllocatedRingBuffer


def test_memory_pool_returns_nearest_sample_and_force():
    pool = PreAllocatedRingBuffer(capacity_frames=8)
    def frame(ts, pose_seed, force):
        pose = [float(pose_seed + i) for i in range(16)]
        joints = [float(i) for i in range(7)]
        return (ts, *pose, *joints, force, 1)

    pool.write_frame_zero_copy(frame(100, 10, 1.5))
    pool.write_frame_zero_copy(frame(200, 20, 2.5))
    pool.write_frame_zero_copy(frame(300, 30, 3.5))

    sample = pool.evaluate_sample_at(240)
    assert sample is not None
    assert sample["timestamp_ns"] == 200
    assert sample["force_z"] == 2.5
    assert list(sample["tcp_pose"][:3]) == [20.0, 21.0, 22.0]
