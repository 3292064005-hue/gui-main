# Verification artifacts

This directory contains committed verification fixtures and traceability material.

- `current_delivery_fix/` is the committed fixture bundle currently used by repository/profile gates.
- Files under `current_delivery_fix/` are **not** standalone proof of live-controller or HIL validation unless an item explicitly records real-environment provenance.
- `sandbox_repository_proof/` is a historical sandbox proof bundle retained for traceability only.

When reviewing a delivery, treat these files as repository fixtures first. Use `docs/05_verification/VERIFICATION_POLICY.md` to determine whether a claim is static, sandbox, mock-profile, HIL, or live-controller proof.
