# Vendor-first xCore rewrite summary

## Core decisions frozen in this rewrite

- Vendored `third_party/rokae_xcore_sdk/robot` is the default SDK root.
- `cpp_robot_core` remains the only execution authority.
- Robot identity is normalized through one canonical contract.
- Runtime config is checked against official SDK limits before clinical execution.
- Clinical mainline keeps `cartesianImpedance`; `directTorque` stays research-only.

## Main code changes

1. Added `spine_ultrasound_ui/services/sdk_vendor_locator.py`
   - Resolves vendored SDK layout first.
   - Reports include/external/lib/static/model library presence.

2. Added `spine_ultrasound_ui/services/robot_identity_service.py`
   - Canonical identity matrix for `xmate3`, `xmate7`, `xmate_er3_pro`, `xmate_er7_pro`, `xmate_standard_6`.
   - Stores official DH tables and SDK limit envelopes.

3. Reworked `xmate_profile.py`
   - Default identity changed to `xmate3`.
   - Correct xMate3 DH defaults.
   - Clinical default Cartesian impedance now stays within official SDK limits.

4. Reworked `clinical_config_service.py`
   - Applies official-identity mainline defaults.
   - Blocks official limit violations for Cartesian impedance and desired wrench.
   - Emits recommended patches that clip values back into official bounds.

5. Reworked `sdk_capability_service.py`
   - Uses canonical robot identity.
   - Adds checks for supported RT modes and official force/impedance bounds.
   - Mainline sequence now explicitly includes `moveReset()` before NRT execution.

6. Reworked `sdk_environment_doctor_service.py`
   - Uses vendored SDK locator.
   - Detects missing protobuf development headers separately from `protoc`.
   - Reports xMateModel availability from the vendored SDK.

7. Reworked `cpp_robot_core/CMakeLists.txt`
   - Vendor-first SDK resolution.
   - Added `FindVendoredRokaeSdk.cmake`.
   - Imported targets `Rokae::xCoreSDK` and `Rokae::xMateModel`.

8. Reworked `scripts/start_real.sh`
   - Uses vendored SDK by default.
   - Enables xMateModel automatically when present.
   - Exports SDK library path for runtime linking.

9. Updated `SdkRobotFacade`
   - Legal default RT parameters.
   - Distinguishes vendored SDK vs vendored SDK + xMateModel runtime source.

10. Updated tests
   - Added vendor SDK / identity / official limit coverage.
   - Updated xMate mainline assertions to `xmate3`.

## Remaining external blockers in this container

- Protobuf development headers are missing, so full CMake configure for `cpp_robot_core` cannot complete in this container.
- `protoc` is also missing.
- TLS runtime material is not populated.

The project code is now vendor-first and correctly surfaces these as environment blockers instead of silently misclassifying the SDK itself as missing.
