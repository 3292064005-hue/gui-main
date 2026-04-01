# TLS material

The repository no longer stores a committed private key.

Generate development-only TLS material before starting `robot_core` or any TLS-backed mock server:

```bash
./scripts/generate_dev_tls_cert.sh
```

This writes a self-signed certificate and private key to `configs/tls/runtime/`.
For clinical or shared environments, mount `ROBOT_CORE_TLS_CERT` and `ROBOT_CORE_TLS_KEY` from a secure secret store instead of committing them.


No certificate or key is committed to the repository root `configs/tls/`; only runtime-generated material under `configs/tls/runtime/` should exist on a development machine.
