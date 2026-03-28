#!/bin/bash
# Spine Ultrasound Platform - Ubuntu 22.04 Hard-RT Setup Script
# MUST BE RUN AS ROOT

set -e

echo "[+] Securing Ubuntu 22.04 for Medical Robotics Hard Real-Time..."

# 1. Isolate CPU 0 and CPU 1 from general Linux kernel scheduling (CFS)
# This prevents random background tasks from interrupting the 1kHz robot loop.
GRUB_FILE="/etc/default/grub"
if grep -q "isolcpus=0,1" "$GRUB_FILE"; then
    echo "[*] GRUB already contains isolcpus=0,1."
else
    echo "[+] Injecting isolcpus=0,1 into GRUB..."
    sed -i 's/GRUB_CMDLINE_LINUX_DEFAULT="/GRUB_CMDLINE_LINUX_DEFAULT="isolcpus=0,1 rcu_nocbs=0,1 nohz_full=0,1 /' "$GRUB_FILE"
    update-grub
    echo "[!] GRUB updated. A reboot is required for CPU isolation to take effect."
fi

# 2. Grant Unlimited Memlock to the real-time robotics group
# Ensures 'mlockall(MCL_CURRENT | MCL_FUTURE)' succeeds without sudo.
LIMITS_FILE="/etc/security/limits.d/99-robotics-rt.conf"
echo "[+] Configuring memory locking limits..."
cat <<EOF > "$LIMITS_FILE"
* soft memlock unlimited
* hard memlock unlimited
* soft rtprio 99
* hard rtprio 99
EOF

echo "[+] Creating systemd target directory..."
mkdir -p /etc/systemd/system/spine-ultrasound.target.wants

echo "[+] Done. System requires reboot to apply CPU partitioning."
