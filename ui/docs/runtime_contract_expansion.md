# Runtime Contract Expansion

This iteration extends the runtime-facing contract surface beyond basic logs and model summaries.

Added authoritative runtime queries:
- `get_identity_contract`
- `get_clinical_mainline_contract`
- `get_session_freeze`
- `get_recovery_contract`

Key effects:
- The C++ core now exposes the resolved robot identity, official mainline mode, and official DH table as a first-class contract.
- Session lock now freezes the clinical runtime config snapshot, including impedance and desired wrench.
- Runtime asset aggregation surfaces recovery and freeze contracts to the operator workstation, reducing hidden state.
- Mock/runtime parity is improved so the desktop sees the same contract surface in both backends.

Additional convergence in this iteration:
- Dispatcher builds a `RuntimeCommandInvocation` from the manifest-backed typed payload contract before resolving the runtime handler.
- The invocation now owns a `RuntimeCommandRequest` parsed payload plus a generated `RuntimeTypedRequestVariant` family (`ConnectRobotRequest`, `LockSessionRequest`, `ValidateScanPlanRequest`, …). Generated response contracts now also publish `data_required_fields` plus typed `data_fields` (field type + nested required keys). Reply validation enforces those reply data shapes instead of relying on envelope tokens only.
- Core runtime handlers consume `RuntimeCommandInvocation` instead of raw request-id/JSON-line pairs, and field-bearing session / validation / execution commands now resolve a command-specific typed request struct before executing write/read logic. The reply side now validates required response-data fields and nested object keys against the generated response-field contract.
- Dispatcher now routes through a generated typed-handler adapter family in `cpp_robot_core/include/robot_core/generated_runtime_command_typed_handlers.inc`, so each canonical command reaches the runtime through a command-specific typed handler adapter before the grouped implementation surface executes.
- Generated request-family artifacts live in `cpp_robot_core/include/robot_core/generated_runtime_command_request_types.h`, `generated_runtime_command_request_parsers.inc`, and `generated_runtime_command_typed_handlers.inc`, and are regenerated from `schemas/runtime_command_manifest.json` alongside the existing request/guard/response contracts.
- Guard and reply-envelope contracts are enforced around handler execution, while projection-only fields remain outside the canonical authority envelope.

- Generated typed handler declarations now publish command-specific entrypoints such as `handleConnectRobotTyped`, `handleLockSessionTyped`, and `handleValidateScanPlanTyped`, while the generated typed-handler adapters route dispatcher traffic through these command-scoped typed methods before compatibility grouping.


- reply contract 现在会继续校验 `data_fields` 中数组字段的元素 shape；对 `logs/projects/paths/active_faults/required_sequence` 这类数组字段，会验证元素类型及对象元素的必需 keys。

- Response contract enforcement now coexists with committed RT phase metrics fixtures and array item constraints for reply data surfaces, but it still does not replace live HIL or controller truth.
