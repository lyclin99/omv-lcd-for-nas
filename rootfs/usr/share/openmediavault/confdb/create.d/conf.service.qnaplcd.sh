#!/bin/sh
set -e

. /usr/share/openmediavault/scripts/helper-functions

if ! omv_config_exists "/config/services/qnaplcd"; then
	omv_config_add_node "/config/services" "qnaplcd"
	omv_config_add_key "/config/services/qnaplcd" "enable" "1"
	omv_config_add_key "/config/services/qnaplcd" "blanktimeout" "30"
	omv_config_add_key "/config/services/qnaplcd" "networkregex" "^eth|^enp|^bond"
fi
for k in showhost showboot showmemory showdisks shownetwork showclock showcustom; do
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
