#!/bin/sh
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

. /usr/share/openmediavault/scripts/helper-functions

if ! omv_config_exists "/config/services/qnaplcd"; then
	omv_config_add_node "/config/services" "qnaplcd"
	omv_config_add_key "/config/services/qnaplcd" "enable" "1"
	omv_config_add_key "/config/services/qnaplcd" "blanktimeout" "30"
	omv_config_add_key "/config/services/qnaplcd" "networkregex" "^eth|^enp|^bond"
fi
for k in showdiskalert showhost showboot showmemory showdisks shownetwork showclock showcustom; do
	if ! omv_config_exists "/config/services/qnaplcd/${k}"; then
		omv_config_add_key "/config/services/qnaplcd" "${k}" "1"
	fi
done
if ! omv_config_exists "/config/services/qnaplcd/customtext"; then
	omv_config_add_key "/config/services/qnaplcd" "customtext" ""
fi

i=0
for k in custom host clock boot memory disks network; do
	i=$((i + 1))
	if ! omv_config_exists "/config/services/qnaplcd/order${k}"; then
		omv_config_add_key "/config/services/qnaplcd" "order${k}" "${i}"
	fi
done

exit 0
