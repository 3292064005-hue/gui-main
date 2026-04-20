---
category: spec
authority: canonical
audience: runtime developers, release engineers
owner: cpp_robot_core
status: active
---

# xCore SDK Integration Guide

## Purpose
Project-internal integration guidance derived from the vendor SDK manual and the repository mainline.

## Network and control assumptions
- Real-time control is based on a 1 ms controller cycle.
- Client-side command generation and send discipline must sustain at least 1 kHz.
- Real-time control should prefer wired direct networking.

## Build and model flags
- xMate model support must be enabled explicitly at build time when authoritative model validation is required.
- The project must detect and report whether SDK/model support is:
  - unavailable
  - vendored-only
  - live-bound and usable

## Model capability usage
When model support is enabled and live binding is established, the authoritative validation path may use:
- `robot.model()`
- inverse kinematics / joint-position solving
- Jacobian computation
- torque model queries

## Single control source
RobotAssist/RCI coexistence must be treated as an operational hazard. The repository assumes a single control source for authoritative runtime decisions.
