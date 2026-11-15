# OMV LCD for NAS

OpenMediaVault 8 web UI plugin to configure the front LCD of QNAP NAS units (tested on TS-459 Pro II), built on [mpeirone/QnapLcdInfo](https://github.com/mpeirone/QnapLcdInfo).

## Features
- Services > OMV LCD for NAS settings page (enable, screen timeout, network filter)
- Pages: custom text (Chinese/ASCII input; LCD shows non-ASCII as `?`), hostname/load, date & time (`yyyy/MM/dd` + `HH:mm:ss`), last boot, memory/swap, disk usage, network
- Per-page show checkbox and adjustable display position
- Browser LCD simulator at `http://<omv>/qnaplcd/` (login to OMV first; ▲/▼ buttons or arrow keys)
- Traditional Chinese UI strings

## Install / remove
```sh
git clone https://github.com/lyclin99/omv-lcd-for-nas && cd omv-lcd-for-nas
sudo ./install.sh      # ./uninstall.sh to remove
```
Then tick **Enabled**, save and apply in the web UI.

Notes: the zh_TW strings are merged into OMV's translation file and may need re-installing after OMV package updates.
