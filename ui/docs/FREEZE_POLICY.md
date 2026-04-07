# MAINLINE_FREEZE

## Frozen mainline rules

1. `cpp_robot_core` is the only write-authority over robot motion.
2. Python, Web, headless, and ROS2 layers may request commands but may not bypass the core.
3. The realtime loop is fixed-period and remains inside C++.
4. Mock and lab semantics must never leak into live authoritative semantics.
5. The runtime final verdict is authoritative; UI/advisory layers may summarize but not replace it.
6. `directTorque` stays outside the default clinical/research mainline.
7. Every execution session must produce a frozen session manifest and evidence lineage.

## Forbidden semantic drifts

- `simulated_contract` inside live authoritative contracts
- `secondary_control_path`
- `duplicate_final_verdict`
- `adaptive_rt_period` inside the official 1 ms mainline
- `ui_runtime_truth`
