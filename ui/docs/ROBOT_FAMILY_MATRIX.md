# ROBOT_FAMILY_MATRIX

This repository is frozen to the **xMateRobot-only** clinical mainline.

## xmate3_cobot_6
- sdk class: `xMateRobot`
- robot model: `xmate3`
- axis count: `6`
- controller series: `xCore`
- realtime mainline: `cartesianImpedance`
- supports xMateModel: yes
- supports planner: yes
- supports drag/path replay: yes
- single control source: required
- preferred link: `wired_direct`

## Rejected families
The following families are intentionally **not** part of the runtime mainline and
must be rejected by configuration / identity resolution:

- `xMateErProRobot`
- `StandardRobot`
- `PCB4Robot`
- `PCB3Robot`
- any `axis_count != 6`
