# Control plane rewrite - wave B

This wave turns the v10 transition state into a more converged platform shape.

## What changed

1. **Headless session evidence is no longer embedded in `HeadlessAdapter`**  
   `HeadlessSessionProductsReader` now owns report/replay/diagnostics/assessment/integrity/release-gate style reads. The adapter keeps transport, lease, and event responsibilities.

2. **HTTP write commands are profile-aware**  
   `ApiCommandGuardService` normalizes command provenance (`actor/workspace/session/lease/intent/profile`) and blocks invalid writers before the adapter is asked to execute anything.

3. **Frontend state now has a canonical home**  
   `ui_frontend/src/state/` is the single intended import surface. Legacy paths exist only as shims.

4. **Desktop persistence has its own boundary**  
   `RuntimePersistenceService` owns runtime-config persistence, UI-layout persistence, and workspace metadata snapshots.

5. **Committed TLS private key removed**  
   Development TLS material is now generated locally with `scripts/generate_dev_tls_cert.sh` or injected through environment variables.
