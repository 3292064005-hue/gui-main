# Sandbox Repository Proof Artifacts

This directory contains machine-readable proof files generated from the repository itself for the current delivery package.

Executed evidence steps:
- repository hygiene gate
- protocol / identity / architecture / python compile gates
- targeted repository-proof regression batch (`36 passed` for touched-area validation in this delivery)
- C++ build evidence in `mock` profile with bounded per-target timeout
- verification execution report
- acceptance summary with embedded verification snapshot

Boundary:
- These files prove **已静态确认 / 已沙箱验证** only.
- They do **not** prove live-controller, HIL, or production deployment validation.
- `build_evidence_report.json` closes through `syntax_only_fallback`, not a full target build.

Path policy:
- Package-contained proof references use relative paths anchored to the proof file directory.
- Ephemeral sandbox build directories are represented symbolically rather than as host-specific absolute paths.
- Host tool paths may remain absolute because they describe the review machine rather than packaged assets.

Authoritative files:
- `build_evidence_report.json`
- `runtime_readiness_manifest.json`
- `verification_execution_report.json`
- `acceptance_summary.json`
