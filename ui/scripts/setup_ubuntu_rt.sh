#!/bin/bash
# Spine Ultrasound Platform - Ubuntu 22.04 Hard-RT Setup Script
# MUST BE RUN AS ROOT

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_SAMPLE="$REPO_ROOT/configs/systemd/spine-cpp-core.env"
ENV_TARGET="/etc/default/spine-cpp-core"
SERVICE_SAMPLE="$REPO_ROOT/configs/systemd/spine-cpp-core.service"
SERVICE_TARGET="/etc/systemd/system/spine-cpp-core.service"

if [ ! -f "$ENV_SAMPLE" ]; then
    echo "[-] Missing RT host contract sample: $ENV_SAMPLE" >&2
    exit 1
fi

echo "[+] Securing Ubuntu 22.04 for Medical Robotics Hard Real-Time..."

# 1. Install the canonical RT host contract only when the target host does not
#    already have an operator-edited contract. Existing /etc/default state is
#    the source of truth for re-runs so CPU/scheduler changes survive setup.
if [ ! -f "$ENV_TARGET" ]; then
    echo "[+] Installing RT host contract sample to $ENV_TARGET ..."
    install -m 0644 "$ENV_SAMPLE" "$ENV_TARGET"
else
    echo "[+] Reusing existing RT host contract from $ENV_TARGET ..."
fi
# shellcheck disable=SC1090
source "$ENV_TARGET"
CPU_SET="${SPINE_RT_CPU_SET:-}"
SCHED_POLICY="${SPINE_RT_SCHED_POLICY:-}"
SCHED_PRIORITY="${SPINE_RT_SCHED_PRIORITY:-}"
FIXED_HOST_ID="${SPINE_RT_FIXED_HOST_ID:-}"
REQUIRE_FIXED_HOST_ID="${SPINE_RT_REQUIRE_FIXED_HOST_ID:-}"
if [ -z "$CPU_SET" ]; then
    echo "[-] SPINE_RT_CPU_SET is required in $ENV_TARGET" >&2
    exit 1
fi
if [ -z "$SCHED_POLICY" ]; then
    echo "[-] SPINE_RT_SCHED_POLICY is required in $ENV_TARGET" >&2
    exit 1
fi
if [ -z "$SCHED_PRIORITY" ]; then
    echo "[-] SPINE_RT_SCHED_PRIORITY is required in $ENV_TARGET" >&2
    exit 1
fi
if [ "${REQUIRE_FIXED_HOST_ID}" = "1" ] && [ -z "$FIXED_HOST_ID" ]; then
    echo "[-] SPINE_RT_FIXED_HOST_ID is required when SPINE_RT_REQUIRE_FIXED_HOST_ID=1 in $ENV_TARGET" >&2
    exit 1
fi
if [ "${REQUIRE_FIXED_HOST_ID}" = "1" ]; then
    CURRENT_HOST_ID="$(hostname)"
    if [ "$CURRENT_HOST_ID" != "$FIXED_HOST_ID" ]; then
        echo "[-] This RT contract is pinned to $FIXED_HOST_ID, but current host is $CURRENT_HOST_ID" >&2
        exit 1
    fi
fi
case "${SCHED_POLICY,,}" in
    fifo|rr) ;;
    *)
        echo "[-] SPINE_RT_SCHED_POLICY must be fifo or rr in $ENV_TARGET" >&2
        exit 1
        ;;
esac
if ! [[ "$SCHED_PRIORITY" =~ ^[0-9]+$ ]]; then
    echo "[-] SPINE_RT_SCHED_PRIORITY must be an integer in $ENV_TARGET" >&2
    exit 1
fi
CPU_SET_SYSTEMD="${CPU_SET//,/ }"

# 2. Align GRUB CPU isolation with the explicit RT host contract.
GRUB_FILE="/etc/default/grub"
echo "[+] Aligning GRUB CPU isolation with SPINE_RT_CPU_SET=$CPU_SET ..."
python3 - "$GRUB_FILE" "$CPU_SET" <<'PY'
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
cpu_set = sys.argv[2]
text = path.read_text(encoding='utf-8')
cmdline = f"isolcpus={cpu_set} rcu_nocbs={cpu_set} nohz_full={cpu_set}"
pattern = re.compile(r'^(GRUB_CMDLINE_LINUX_DEFAULT=")(.*?)(")$', re.MULTILINE)
match = pattern.search(text)
if not match:
    raise SystemExit("GRUB_CMDLINE_LINUX_DEFAULT not found in /etc/default/grub")
current = match.group(2)
for token in ("isolcpus", "rcu_nocbs", "nohz_full"):
    current = re.sub(rf'(^|\s){token}=[^\s"]+', ' ', current).strip()
updated = (cmdline + ' ' + current).strip()
text = text[:match.start()] + match.group(1) + updated + match.group(3) + text[match.end():]
path.write_text(text, encoding='utf-8')
PY
update-grub
echo "[!] GRUB updated. A reboot is required for CPU isolation to take effect."

# 3. Grant Unlimited Memlock to the real-time robotics group
LIMITS_FILE="/etc/security/limits.d/99-robotics-rt.conf"
echo "[+] Configuring memory locking limits..."
cat <<EOF > "$LIMITS_FILE"
* soft memlock unlimited
* hard memlock unlimited
* soft rtprio 99
* hard rtprio 99
EOF

# 4. Install or refresh the systemd service template with a CPUAffinity line
#    rendered from the explicit RT host contract.
if [ -f "$SERVICE_SAMPLE" ]; then
    echo "[+] Installing rendered systemd unit to $SERVICE_TARGET ..."
    python3 - "$SERVICE_SAMPLE" "$SERVICE_TARGET" "$CPU_SET_SYSTEMD" "$SCHED_POLICY" "$SCHED_PRIORITY" <<'PY'
import sys
from pathlib import Path

src = Path(sys.argv[1])
dst = Path(sys.argv[2])
cpu_affinity = sys.argv[3]
sched_policy = sys.argv[4].lower()
sched_priority = sys.argv[5]
text = src.read_text(encoding='utf-8')
lines = []
for line in text.splitlines():
    if line.startswith('CPUAffinity='):
        lines.append(f'CPUAffinity={cpu_affinity}')
    elif line.startswith('CPUSchedulingPolicy='):
        lines.append(f'CPUSchedulingPolicy={sched_policy}')
    elif line.startswith('CPUSchedulingPriority='):
        lines.append(f'CPUSchedulingPriority={sched_priority}')
    else:
        lines.append(line)
dst.write_text('\n'.join(lines) + '\n', encoding='utf-8')
PY
    chmod 0644 "$SERVICE_TARGET"
    systemctl daemon-reload || true
fi

mkdir -p /etc/systemd/system/spine-ultrasound.target.wants

echo "[+] Done. System requires reboot to apply CPU partitioning."
echo "[+] After reboot, verify /sys/kernel/realtime == 1, confirm hostname matches SPINE_RT_FIXED_HOST_ID, confirm CPUAffinity/CPUSchedulingPolicy/CPUSchedulingPriority in $SERVICE_TARGET match $ENV_TARGET, then run python scripts/doctor_runtime.py --strict --json."
