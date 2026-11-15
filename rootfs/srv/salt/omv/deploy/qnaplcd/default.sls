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
{% set _ = salt['omv_utils.register_jinja_filters']() %}
{% set config = salt['omv_conf.get']('conf.service.qnaplcd') %}

{% if config.enable | to_bool %}

configure_lcdinfo_environment:
  file.managed:
    - name: "/etc/default/lcdinfo"
    - contents: |
        LCD_BLANK_TIMEOUT="{{ config.blanktimeout }}"
        LCD_NETWORK_REGEX="{{ config.networkregex }}"
        LCD_SHOW_DISKALERT="{{ 1 if config.showdiskalert | to_bool else 0 }}"
        LCD_SHOW_HOST="{{ 1 if config.showhost | to_bool else 0 }}"
        LCD_SHOW_BOOT="{{ 1 if config.showboot | to_bool else 0 }}"
        LCD_SHOW_MEMORY="{{ 1 if config.showmemory | to_bool else 0 }}"
        LCD_SHOW_DISKS="{{ 1 if config.showdisks | to_bool else 0 }}"
        LCD_SHOW_NETWORK="{{ 1 if config.shownetwork | to_bool else 0 }}"
        LCD_SHOW_CLOCK="{{ 1 if config.showclock | to_bool else 0 }}"
        LCD_SHOW_CUSTOM="{{ 1 if config.showcustom | to_bool else 0 }}"
        LCD_CUSTOM_TEXT="{{ config.customtext }}"
        LCD_ORDER_CUSTOM="{{ config.ordercustom }}"
        LCD_ORDER_HOST="{{ config.orderhost }}"
        LCD_ORDER_CLOCK="{{ config.orderclock }}"
        LCD_ORDER_BOOT="{{ config.orderboot }}"
        LCD_ORDER_MEMORY="{{ config.ordermemory }}"
        LCD_ORDER_DISKS="{{ config.orderdisks }}"
        LCD_ORDER_NETWORK="{{ config.ordernetwork }}"
    - user: root
    - group: root
    - mode: '0644'

start_lcdinfo_service:
  service.running:
    - name: lcdinfo
    - enable: True
    - watch:
      - file: configure_lcdinfo_environment

{% else %}

stop_lcdinfo_service:
  service.dead:
    - name: lcdinfo
    - enable: False

{% endif %}
