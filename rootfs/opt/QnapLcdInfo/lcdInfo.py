#!/usr/bin/env python3
import psutil, socket, re, threading, datetime, time, os, sys, json, subprocess

DUMP = "--dump-json" in sys.argv
if not DUMP:
        from qnapdisplay import QnapDisplay
        Lcd = QnapDisplay()
infoIndex = 0
t = None
blankLcdTimeout = int(os.environ.get("LCD_BLANK_TIMEOUT", "5"))
networkRegex = os.environ.get("LCD_NETWORK_REGEX", "^eth|^enp|^bond")
lock = threading.Lock()
screenOn = True
current = [None]
CLOCK = object()

SMART_CACHE_FILE = "/run/lcdinfo_smart_cache.json"
TEST_ALERT_FILE = "/run/lcdinfo_test_alert"
SMART_CACHE_TTL = 30
smartCacheLock = threading.Lock()
smartMemCache = {"ts": 0.0, "by_dev": {}, "alerts": []}

class AlertPage(list):
        pass

def show(name):
        return os.environ.get("LCD_SHOW_" + name, "1") == "1"

def ascii16(text):
        # The LCD only has an ASCII/Japanese font, replace other characters
        return "".join(c if 32 <= ord(c) < 127 else "?" for c in text)

DEFAULT_ORDER = ["CUSTOM", "HOST", "CLOCK", "BOOT", "MEMORY", "DISKS", "NETWORK"]

def position(name):
        try:
                return int(os.environ.get("LCD_ORDER_" + name, ""))
        except ValueError:
                return DEFAULT_ORDER.index(name) + 1

def checkRaidAndBlockAlerts():
        alerts = []
        # 1. Optional test alert trigger file (/run/lcdinfo_test_alert)
        if os.path.exists(TEST_ALERT_FILE):
                try:
                        with open(TEST_ALERT_FILE, "r", encoding="utf-8", errors="ignore") as f:
                                lines = [l.strip() for l in f.read().splitlines() if l.strip()]
                        l0 = ascii16(lines[0])[:16] if len(lines) > 0 else "! DISK ALERT !"
                        l1 = ascii16(lines[1])[:16] if len(lines) > 1 else "sdb BAD SEC:8"
                        alerts.append([l0, l1])
                except Exception:
                        alerts.append(["! DISK ALERT !", "sdb BAD SEC:8"])

        # 2. Software RAID (/proc/mdstat) degraded or faulty member check
        if os.path.exists("/proc/mdstat"):
                try:
                        with open("/proc/mdstat", "r", encoding="utf-8", errors="ignore") as f:
                                mdstat = f.read()
                        current_md = None
                        for line in mdstat.splitlines():
                                m_dev = re.match(r"^(md\d+)\s*:\s*(\S+)\s+(.*)$", line)
                                if m_dev:
                                        current_md = m_dev.group(1)
                                        state = m_dev.group(2)
                                        rest = m_dev.group(3)
                                        if state == "inactive":
                                                alerts.append(["! RAID ALERT !", f"{current_md} INACTIVE"[:16]])
                                        for fdev in re.findall(r"([a-zA-Z0-9_]+)\[\d+\]\(F\)", rest):
                                                alerts.append(["! RAID ALERT !", f"{current_md} FAIL:{fdev}"[:16]])
                                elif current_md:
                                        m_stat = re.search(r"\[(\d+)/(\d+)\]\s+\[([U_]+)\]", line)
                                        if m_stat:
                                                total = int(m_stat.group(1))
                                                active = int(m_stat.group(2))
                                                u_str = m_stat.group(3)
                                                if active < total or "_" in u_str:
                                                        msg = f"{current_md} [{active}/{total}] {u_str}"
                                                        if len(msg) > 16:
                                                                msg = f"{current_md} DEGRAD {active}/{total}"
                                                        alerts.append(["! RAID ALERT !", msg[:16]])
                                        if not line.strip():
                                                current_md = None
                except Exception:
                        pass

        # 3. Block device state in /sys/block
        if os.path.isdir("/sys/block"):
                try:
                        for dev in sorted(os.listdir("/sys/block")):
                                if re.match(r"^(loop|ram|md|dm-|sr|zram|fd|nbd)", dev):
                                        continue
                                state_file = f"/sys/block/{dev}/device/state"
                                if os.path.exists(state_file):
                                        with open(state_file, "r", encoding="utf-8", errors="ignore") as f:
                                                st = f.read().strip().lower()
                                        if st in ("offline", "transport-offline", "faulty", "dead"):
                                                alerts.append(["! DISK ALERT !", f"{dev} OFFLINE"[:16]])
                except Exception:
                        pass

        return alerts

def checkSmartAlerts(force=False):
        now = time.time()
        with smartCacheLock:
                if not force and smartMemCache["ts"] > 0 and (now - smartMemCache["ts"]) < SMART_CACHE_TTL:
                        return list(smartMemCache["alerts"])

        if DUMP and not force and os.path.exists(SMART_CACHE_FILE):
                try:
                        with open(SMART_CACHE_FILE, "r", encoding="utf-8") as f:
                                cached = json.load(f)
                        if (now - float(cached.get("ts", 0))) < 60:
                                return cached.get("alerts", [])
                except Exception:
                        pass

        smartctl_bin = "/usr/sbin/smartctl" if os.path.exists("/usr/sbin/smartctl") else "smartctl"
        alerts = []
        by_dev = {}
        with smartCacheLock:
                prev_by_dev = dict(smartMemCache.get("by_dev", {}))

        if os.path.isdir("/sys/block"):
                for dev in sorted(os.listdir("/sys/block")):
                        if re.match(r"^(loop|ram|md|dm-|sr|zram|fd|nbd)", dev):
                                continue
                        dev_path = f"/dev/{dev}"
                        if not os.path.exists(dev_path):
                                continue
                        try:
                                proc = subprocess.run(
                                        [smartctl_bin, "-n", "standby,0", "-j", "-H", "-A", dev_path],
                                        capture_output=True, text=True, timeout=5
                                )
                                data = json.loads(proc.stdout) if proc.stdout.strip() else {}
                        except Exception:
                                continue

                        # If drive is in standby, preserve previous SMART alerts for this drive
                        exit_status = data.get("smartctl", {}).get("exit_status", 0)
                        if data.get("power_mode", {}).get("is_standby") or (
                                "smart_status" not in data and exit_status == 2
                        ):
                                dev_alerts = prev_by_dev.get(dev, [])
                                by_dev[dev] = dev_alerts
                                alerts.extend(dev_alerts)
                                continue

                        if (
                                "smart_status" not in data
                                and "ata_smart_attributes" not in data
                                and "nvme_smart_health_information_log" not in data
                        ):
                                continue

                        dev_alerts = []
                        passed = data.get("smart_status", {}).get("passed")
                        if passed is False:
                                dev_alerts.append(["! DISK ALERT !", f"{dev} SMART FAIL"[:16]])

                        # Check ATA SMART attributes (ID 5, 197, 198 + failing now)
                        table = data.get("ata_smart_attributes", {}).get("table", [])
                        bad_sectors = 0
                        attr_failed = False
                        for attr in table:
                                aid = attr.get("id")
                                wf = str(attr.get("when_failed", "")).strip().upper()
                                if wf == "NOW":
                                        attr_failed = True
                                if aid in (5, 197, 198):
                                        raw_obj = attr.get("raw", {})
                                        raw_parts = str(raw_obj.get("string", "")).strip().split()
                                        try:
                                                val = int(raw_parts[0]) if raw_parts else int(raw_obj.get("value", 0))
                                        except ValueError:
                                                val = int(raw_obj.get("value", 0))
                                        if val > 0:
                                                bad_sectors += val

                        if bad_sectors > 0:
                                dev_alerts.append(["! DISK ALERT !", f"{dev} BAD SEC:{bad_sectors}"[:16]])
                        elif attr_failed and passed is not False:
                                dev_alerts.append(["! DISK ALERT !", f"{dev} ATTR FAIL"[:16]])

                        # Check NVMe SMART log
                        nvme = data.get("nvme_smart_health_information_log", {})
                        if nvme:
                                media_err = int(nvme.get("media_errors", 0) or 0)
                                crit_warn = int(nvme.get("critical_warning", 0) or 0)
                                avail_spare = nvme.get("available_spare")
                                spare_thresh = nvme.get("available_spare_threshold")
                                if media_err > 0:
                                        dev_alerts.append(["! DISK ALERT !", f"{dev} BAD SEC:{media_err}"[:16]])
                                elif crit_warn > 0 or (
                                        avail_spare is not None and spare_thresh is not None and avail_spare < spare_thresh
                                ):
                                        dev_alerts.append(["! DISK ALERT !", f"{dev} NVME WARN"[:16]])

                        # Check SCSI grown defect list
                        defects = int(data.get("scsi_grown_defect_list", 0) or 0)
                        if defects > 0:
                                dev_alerts.append(["! DISK ALERT !", f"{dev} DEFECT:{defects}"[:16]])

                        by_dev[dev] = dev_alerts
                        alerts.extend(dev_alerts)

        with smartCacheLock:
                smartMemCache["ts"] = now
                smartMemCache["by_dev"] = by_dev
                smartMemCache["alerts"] = alerts

        try:
                tmp_file = SMART_CACHE_FILE + ".tmp"
                with open(tmp_file, "w", encoding="utf-8") as f:
                        json.dump({"ts": now, "alerts": alerts}, f)
                os.replace(tmp_file, SMART_CACHE_FILE)
        except Exception:
                pass

        return list(alerts)

def getDiskAlerts(force_smart=False):
        if not show("DISKALERT"):
                return []
        combined = []
        for item in checkRaidAndBlockAlerts() + checkSmartAlerts(force=force_smart):
                if item not in combined:
                        combined.append(item)
        return combined

def getDataArray(network_regex=networkRegex):
        pages = {}
        text = os.environ.get("LCD_CUSTOM_TEXT", "").strip()
        if show("CUSTOM") and text:
                text = ascii16(text)
                pages["CUSTOM"] = [[text[:16], text[16:32]]]
        if show("HOST"):
                pages["HOST"] = [[socket.gethostname(),"Load(5m): "+ str(psutil.getloadavg()[1])]]
        if show("CLOCK"):
                pages["CLOCK"] = [CLOCK]
        if show("BOOT"):
                pages["BOOT"] = [["Last boot:", datetime.datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S")]]
        if show("MEMORY"):
                pages["MEMORY"] = [["Memory: "+str(psutil.virtual_memory().percent)+"%","Swap: "+str(psutil.swap_memory().percent)+"%"]]
        if show("DISKS"):
                pages["DISKS"] = [["Usage " + d.mountpoint, str(psutil.disk_usage(d.mountpoint).percent)+ "%"] for d in psutil.disk_partitions()]
        if show("NETWORK"):
                networks = psutil.net_if_addrs()
                pages["NETWORK"] = [[n, networks[n][0].address] for n in networks if networks[n][0].netmask and re.search(network_regex, n)]
        output = [AlertPage(a) for a in getDiskAlerts()]
        for name in sorted(pages, key=lambda n: (position(n), DEFAULT_ORDER.index(n))):
                output.extend(pages[name])
        if not output:
                output.append([socket.gethostname(), ""])
        return(output)

def render(entry):
        if entry is CLOCK:
                now = datetime.datetime.now()
                entry = [now.strftime("%Y/%m/%d"), now.strftime("%H:%M:%S")]
        with lock:
                Lcd.Write(0, entry[0])
                Lcd.Write(1, entry[1])

def clockTicker():
        global screenOn, infoIndex, t
        # Lcd.Read() blocks until a button is pressed, so refresh the clock and monitor disk alerts here
        last_alerts = getDiskAlerts()
        tick = 0
        while True:
                time.sleep(1)
                tick += 1
                if current[0] is CLOCK and screenOn:
                        render(CLOCK)
                if tick % 2 == 0 and show("DISKALERT"):
                        alerts = getDiskAlerts()
                        if alerts:
                                if alerts != last_alerts or not screenOn:
                                        # Wake up LCD and jump immediately to first alert page
                                        if t:
                                                t.cancel()
                                        with lock:
                                                screenOn = True
                                                Lcd.Enable()
                                        infoIndex = 0
                                        alert_entry = AlertPage(alerts[0])
                                        current[0] = alert_entry
                                        render(alert_entry)
                                elif len(alerts) > 1 and isinstance(current[0], AlertPage) and tick % 4 == 0:
                                        # Cycle through multiple active alerts on the LCD
                                        infoIndex = (infoIndex + 1) % len(alerts)
                                        alert_entry = AlertPage(alerts[infoIndex])
                                        current[0] = alert_entry
                                        render(alert_entry)
                        elif last_alerts and not alerts:
                                # Alerts cleared: return to normal page and re-arm blank timeout
                                data = getDataArray()
                                infoIndex = 0
                                current[0] = data[0]
                                if screenOn:
                                        render(data[0])
                                t = timerReset(t)
                        last_alerts = alerts

def timerCallback():
        global screenOn, infoIndex
        data = getDataArray()
        if any(isinstance(e, AlertPage) for e in data):
                # Keep LCD constantly on and return to the alert page when an alert is active
                infoIndex = 0
                current[0] = data[0]
                with lock:
                        screenOn = True
                        Lcd.Enable()
                render(data[0])
                return
        with lock:
                screenOn = False
                Lcd.Disable()

def timerReset(t=None):
        if(t):
                t.cancel()
        if blankLcdTimeout <= 0:
                return None
        t = threading.Timer(blankLcdTimeout, timerCallback)
        t.start()
        return t

if DUMP:
        data = getDataArray()
        pages = []
        for e in data:
                if e is CLOCK:
                        pages.append({"clock": True})
                elif isinstance(e, AlertPage):
                        pages.append({"alert": True, "lines": [e[0], e[1]]})
                else:
                        pages.append(e)
        print(json.dumps({"pages": pages, "timeout": blankLcdTimeout,
                          "has_alert": any(isinstance(e, AlertPage) for e in data),
                          "test_alert": os.path.exists(TEST_ALERT_FILE),
                          "servertime": time.time(),
                          "tzoffset": int(datetime.datetime.now().astimezone().utcoffset().total_seconds())}))
        sys.exit(0)

threading.Thread(target=clockTicker, daemon=True).start()

while(True):
        t = timerReset(t)
        with lock:
                screenOn = True
                Lcd.Enable()
        data= getDataArray()
        infoIndex = infoIndex % len(data)
        current[0] = data[infoIndex]
        render(data[infoIndex])
        if(Lcd.Read() =="Up"):
                delta= -1;
        else:
                delta= +1;
        infoIndex = (infoIndex + delta) % len(data)
