#!/usr/bin/env python3
import psutil, socket, re, threading, datetime, time, os, sys, json

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
        output = []
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
        # Lcd.Read() blocks until a button is pressed, so refresh the clock here
        while True:
                time.sleep(1)
                if current[0] is CLOCK and screenOn:
                        render(CLOCK)

def timerCallback():
        global screenOn
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
        pages = [{"clock": True} if e is CLOCK else e for e in getDataArray()]
        print(json.dumps({"pages": pages, "timeout": blankLcdTimeout,
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
