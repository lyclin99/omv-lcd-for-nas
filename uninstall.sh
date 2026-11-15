#!/bin/bash
# OMV LCD for NAS - OpenMediaVault plugin for the QNAP front LCD
# Copyright (C) 2026 lyclin99
# Based on mpeirone/QnapLcdInfo (GPL-3.0).
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
set -e
[ "$(id -u)" = 0 ] || { echo "Run as root"; exit 1; }
systemctl disable --now lcdinfo 2>/dev/null || true
rm -f /etc/systemd/system/lcdinfo.service /etc/default/lcdinfo \
  /etc/nginx/openmediavault-webgui.d/qnaplcd.conf \
  /usr/share/openmediavault/datamodels/conf.service.qnaplcd.json \
  /usr/share/openmediavault/confdb/create.d/conf.service.qnaplcd.sh \
  /usr/share/openmediavault/engined/rpc/qnaplcd.inc \
  /usr/share/openmediavault/engined/module/qnaplcd.inc \
  /usr/share/openmediavault/workbench/navigation.d/services.qnaplcd.yaml \
  /usr/share/openmediavault/workbench/route.d/services.qnaplcd.yaml \
  /usr/share/openmediavault/workbench/component.d/omv-services-qnaplcd-form-page.yaml
rm -rf /usr/share/openmediavault/qnaplcd /srv/salt/omv/deploy/qnaplcd
systemctl daemon-reload
nginx -t && systemctl reload nginx
omv-mkworkbench all
monit restart omv-engined 2>/dev/null || systemctl restart openmediavault-engined
echo "Removed. /opt/QnapLcdInfo and the OMV config entry were left in place."
