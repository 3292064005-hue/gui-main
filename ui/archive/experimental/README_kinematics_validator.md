# Archived legacy kinematics validator

`archive/experimental/kinematics_validator.cpp` was removed from the production build because it was a non-authoritative placeholder that did not participate in the runtime validation chain.

Authoritative plan feasibility validation now lives in:
- `cpp_robot_core/src/sdk_robot_facade_model.cpp`
- `cpp_robot_core/src/model_authority.cpp`
- `cpp_robot_core/src/scan_plan_validator.cpp`

This archived file is retained only as historical context and must not be reintroduced into the build without a full runtime integration review.
