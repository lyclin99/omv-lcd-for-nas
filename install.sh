#!/bin/bash
# Install "OMV LCD for NAS" (QNAP LCD plugin for OpenMediaVault 8) on a QNAP NAS.
set -e
[ "$(id -u)" = 0 ] || { echo "Run as root"; exit 1; }
HERE="$(cd "$(dirname "$0")" && pwd)"

apt-get update
apt-get install -y git python3-venv

# Upstream LCD driver
if [ ! -d /opt/QnapLcdInfo ]; then
  git clone https://github.com/mpeirone/QnapLcdInfo /opt/QnapLcdInfo
fi
if [ ! -d /opt/QnapLcdInfo/venv ]; then
  python3 -m venv /opt/QnapLcdInfo/venv
  /opt/QnapLcdInfo/venv/bin/pip install -r /opt/QnapLcdInfo/requirements.txt
fi

# Plugin files (copy file by file so existing system directory permissions are never changed)
(cd "$HERE/rootfs" && find . -type d -exec install -d -m 755 "/{}" \;)
(cd "$HERE/rootfs" && find . -type f -exec install -m 644 "{}" "/{}" \;)
chmod 755 /usr/share/openmediavault/confdb/create.d/conf.service.qnaplcd.sh /opt/QnapLcdInfo/lcdInfo.py

systemctl daemon-reload
omv-confdbadm create conf.service.qnaplcd || true
nginx -t && systemctl reload nginx
omv-mkworkbench all

# Traditional Chinese UI strings.
# Must run AFTER omv-mkworkbench, which regenerates assets/i18n/zh_TW.json and drops merged strings.
python3 - "$HERE/i18n/zh_TW.json" <<'EOF'
import json, sys
f = '/var/www/openmediavault/assets/i18n/zh_TW.json'
j = json.load(open(f, encoding='utf-8'))
j.update(json.load(open(sys.argv[1], encoding='utf-8')))
json.dump(j, open(f, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
EOF

monit restart omv-engined 2>/dev/null || systemctl restart openmediavault-engined
omv-salt deploy run qnaplcd

echo "Done. Open OMV > Services > OMV LCD for NAS, tick Enabled, save and apply."
echo "Note: after OMV package updates or 'omv-mkworkbench', re-run ./install.sh to restore the zh_TW strings."
