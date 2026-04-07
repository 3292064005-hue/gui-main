#!/usr/bin/env bash
set -euo pipefail

REMOTE_IP="${1:-192.168.0.160}"
LOCAL_IP="${2:-192.168.0.100}"

echo "[HIL] xMateRobot-only readiness check"
echo "[HIL] remote_ip=${REMOTE_IP}"
echo "[HIL] local_ip=${LOCAL_IP}"

if command -v ip >/dev/null 2>&1; then
  echo "[HIL] Local interface addresses:"
  ip -4 addr show | sed 's/^/  /'
  if ip -4 addr show | grep -q "${LOCAL_IP}"; then
    echo "[HIL] local_ip is present on a host interface"
  else
    echo "[HIL][WARN] local_ip is not currently assigned to any visible interface"
  fi
else
  echo "[HIL][WARN] 'ip' command not found; cannot inspect local interfaces"
fi

if command -v ping >/dev/null 2>&1; then
  if ping -c 1 -W 1 "${REMOTE_IP}" >/dev/null 2>&1; then
    echo "[HIL] remote_ip responds to ICMP"
  else
    echo "[HIL][WARN] remote_ip did not respond to ICMP; controller may still be reachable via the SDK path"
  fi
else
  echo "[HIL][WARN] 'ping' command not found; skipping reachability probe"
fi

if command -v nc >/dev/null 2>&1; then
  echo "[HIL] nc is available for manual UDP checks"
else
  echo "[HIL][WARN] 'nc' not found; manual UDP diagnostics are limited"
fi

echo "[HIL] Next step: use the desktop runtime and confirm live_binding_established=true."
echo "[HIL] Capture get_sdk_runtime_config -> runtime_config.json once the runtime is online."
echo "[HIL] After collecting measured phase metrics, run:"
echo "[HIL]   python scripts/validate_hil_phase_metrics.py --runtime-config runtime_config.json --evidence rt_phase_metrics.json"
