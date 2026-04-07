# TEST_STRATEGY

Stable target surfaces:
- API contract and security
- Control plane and control ownership
- Headless runtime and session products
- Release gate and evidence seal
- Replay/export determinism
- Mainline mock end-to-end workflow
- Preweight measured-only semantic closure
- Deployment profile boundary behavior

Execution:
```bash
pytest
```

For deployment/profile smoke:
```bash
python scripts/deployment_smoke_test.py
```


Preweight semantic closure gate:
```bash
python scripts/run_pytest_mainline.py -q tests/test_preweight_semantic_closure.py
```

This gate verifies that `preweight_deterministic` closes authoritatively when measured evidence is present and fail-closes when the measured chain is missing.
