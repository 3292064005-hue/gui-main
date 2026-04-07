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
