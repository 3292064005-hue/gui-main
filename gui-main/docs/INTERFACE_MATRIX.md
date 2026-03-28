# Interface Matrix

| Layer | Owns robot control? | Reads SDK directly? | Runs RT loop? | Writes experiment data? |
|---|---:|---:|---:|---:|
| cpp_robot_core | Yes | Yes | Yes | No |
| spine_ultrasound_ui/services/robot_core_client.py | No | No | No | No |
| spine_ultrasound_ui/core/experiment_manager.py | No | No | No | Yes |
| spine_ultrasound_ui/imaging/* | No | No | No | Yes |
| ros2_bridge (optional) | No | No | No | Optional |
