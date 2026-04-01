#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TLS_DIR="${ROOT_DIR}/configs/tls/runtime"
mkdir -p "${TLS_DIR}"
CERT="${TLS_DIR}/robot_core_server.crt"
KEY="${TLS_DIR}/robot_core_server.key"
if [[ -f "${CERT}" && -f "${KEY}" ]]; then
  echo "TLS material already exists at ${TLS_DIR}" >&2
  exit 0
fi
openssl req -x509 -nodes -newkey rsa:2048 -keyout "${KEY}" -out "${CERT}" -days 365   -subj "/CN=localhost/O=SpineUltrasound/OU=DevRuntime" >/dev/null 2>&1
chmod 600 "${KEY}"
chmod 644 "${CERT}"
echo "Generated development TLS certificate at ${CERT}" >&2
