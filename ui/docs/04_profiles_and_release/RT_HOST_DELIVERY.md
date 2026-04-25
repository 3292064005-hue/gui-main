---
category: spec
authority: canonical
audience: release engineers, operators, reviewers
owner: cpp_robot_core
status: active
---

# RT Host Delivery

## Purpose
Treat the single fixed RT workstation as a first-class release artifact for mainline delivery.
The runtime binary is not sufficient on its own; the fixed host identity, scheduler, CPU pinning,
memlock, and PREEMPT_RT kernel state are part of the deliverable.

## Canonical artifacts
- `configs/systemd/spine-cpp-core.service`
- `configs/systemd/spine-cpp-core.env`
- `cpp_robot_core/src/rt_host_bootstrap.cpp`
- `scripts/setup_ubuntu_rt.sh`
- `scripts/doctor_runtime.py`

## Contract rules
- `SPINE_RT_HOST_CONTRACT_VERSION`, `SPINE_RT_HOST_CONTRACT_LABEL`, and `SPINE_RT_FIXED_HOST_ID` are mandatory.
- The canonical topology is one fixed workstation: `spine-rt-workstation-01`. Do not expand this into a multi-host matrix without a new architecture decision.
- `SPINE_RT_CPU_SET` is mandatory for any deployment that requires RT affinity.
- `CPUAffinity=` in the systemd unit must match `SPINE_RT_CPU_SET` exactly.
- `CPUSchedulingPolicy` and `CPUSchedulingPriority` in the installed systemd unit must match `SPINE_RT_SCHED_POLICY` and `SPINE_RT_SCHED_PRIORITY` from `/etc/default/spine-cpp-core`.
- `LimitMEMLOCK=infinity` and `LimitRTPRIO=99` remain canonical service settings.
- Mainline fixed-host delivery requires `/sys/kernel/realtime == 1` on the target machine.
- `SPINE_RT_REQUIRE_FIXED_HOST_ID=1` makes runtime bootstrap fail closed when the current hostname does not match `SPINE_RT_FIXED_HOST_ID`.

## Operator install path
1. Run `scripts/setup_ubuntu_rt.sh` as root on the target machine; it installs the sample contract only when `/etc/default/spine-cpp-core` does not already exist.
2. Edit `/etc/default/spine-cpp-core` only for the fixed workstation identity and measured CPU set. `SPINE_RT_FIXED_HOST_ID` must remain the approved host id for that machine.
3. Re-run `scripts/setup_ubuntu_rt.sh` after any env change so the installed systemd unit and GRUB CPU isolation stay aligned with `/etc/default/spine-cpp-core`.
4. Reboot so GRUB CPU isolation and PREEMPT_RT kernel selection take effect.
5. Run `python scripts/doctor_runtime.py --strict --json` on the target machine; the doctor prefers deployed `/etc` artifacts when present and archives the resulting snapshot with the release evidence bundle.

## Release boundary
A repository build without the matching fixed RT host contract only proves code readiness.
It does **not** prove fixed-workstation deployment readiness.
