# TEST_STRATEGY

Stable target surfaces:
- API contract and security
- Control plane and control ownership
- Headless runtime and session products
- Release gate and evidence seal
- Replay/export determinism
- Mainline mock end-to-end workflow
- Deployment profile boundary behavior

Execution:
```bash
pytest
```

For deployment/profile smoke:
```bash
python scripts/deployment_smoke_test.py
```
