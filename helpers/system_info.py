"""
system_info.py — Sammelt Host-Metriken fuer das DEVHUB Dashboard.

Alle Funktionen sind bewusst defensiv geschrieben (try/except), damit ein
fehlendes optionales Paket (psutil/requests) oder eine fehlende
Internetverbindung nicht den ganzen Server zum Absturz bringt — das
Dashboard zeigt dann einfach "N/A" statt einer Fehlerseite.
"""

import getpass
import os
import platform
import socket
import subprocess
import sys
import time

try:
    import requests
except ImportError:
    requests = None

try:
    import psutil
except ImportError:
    psutil = None

IS_WINDOWS = sys.platform == "win32"

# Persistenter Cache fuer Prozess-Objekte, damit psutil sinnvolle
# CPU-Prozentwerte liefern kann (die erste Messung pro Prozess ist immer 0.0,
# siehe psutil-Doku: cpu_percent() misst die Zeit *seit dem letzten Aufruf*).
_proc_cache = {}


def get_username():
    """Der tatsaechliche Windows/Unix-Benutzername des eingeloggten Operators."""
    try:
        return getpass.getuser()
    except Exception:
        return os.environ.get("USERNAME") or os.environ.get("USER") or "OPERATOR"


def get_hostname():
    try:
        return socket.gethostname()
    except Exception:
        return "UNKNOWN-HOST"


def get_battery():
    """Akkustatus, falls vorhanden (Laptops). None auf Desktop-PCs."""
    if psutil is None or not hasattr(psutil, "sensors_battery"):
        return None
    try:
        batt = psutil.sensors_battery()
        if batt is None:
            return None
        return {
            "percent": round(batt.percent, 1),
            "plugged": bool(batt.power_plugged),
        }
    except Exception:
        return None


def ping_latency(host="8.8.8.8", timeout=1.5):
    """Einfache ICMP-Ping-Latenz in ms — ein schneller Gesundheitscheck der
    Internetverbindung. Gibt None zurueck, wenn ping nicht verfuegbar ist
    oder die Anfrage fehlschlaegt (z.B. ICMP von der Firewall geblockt)."""
    try:
        if IS_WINDOWS:
            cmd = ["ping", "-n", "1", "-w", str(int(timeout * 1000)), host]
        else:
            cmd = ["ping", "-c", "1", "-W", str(int(timeout)), host]
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout + 1,
            creationflags=subprocess.CREATE_NO_WINDOW if IS_WINDOWS else 0,
        )
        if result.returncode != 0:
            return None
        out = result.stdout
        import re
        # Windows: "Zeit=12ms" / "time=12ms"  |  Unix: "time=12.3 ms"
        match = re.search(r"(?:time|zeit)[=<]\s*([\d.]+)", out, re.IGNORECASE)
        if match:
            return round(float(match.group(1)), 1)
        return None
    except Exception:
        return None


def get_local_ip():
    """Lokale LAN-IP ermitteln, ohne tatsaechlich Pakete zu senden (UDP-Trick)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


def get_public_ip_and_geo():
    """Oeffentliche IP + Geolocation via ip-api.com (kostenlos, kein Key noetig)."""
    if requests is None:
        return {"error": "Python-Paket 'requests' fehlt"}
    try:
        r = requests.get("http://ip-api.com/json/", timeout=4)
        data = r.json()
        if data.get("status") == "success":
            return {
                "ip": data.get("query"),
                "city": data.get("city"),
                "region": data.get("regionName"),
                "country": data.get("country"),
                "isp": data.get("isp"),
                "lat": data.get("lat"),
                "lon": data.get("lon"),
                "timezone": data.get("timezone"),
            }
        return {"error": "Geolocation-Abfrage fehlgeschlagen"}
    except Exception as e:
        return {"error": str(e)}


def get_system_stats():
    """CPU/RAM/Disk-Auslastung sowie Boot-Zeit fuer die Uptime-Anzeige."""
    if psutil is None:
        return {"error": "Python-Paket 'psutil' fehlt"}
    try:
        return {
            "cpu_percent": psutil.cpu_percent(interval=0.2),
            "ram_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage(os.path.abspath(os.sep)).percent,
            "boot_time": psutil.boot_time(),
        }
    except Exception as e:
        return {"error": str(e)}


def top_processes(limit=8):
    """Liefert die Top-Prozesse nach CPU-Auslastung."""
    if psutil is None:
        return []

    current_pids = set()
    for p in psutil.process_iter(["pid"]):
        pid = p.info["pid"]
        current_pids.add(pid)
        if pid not in _proc_cache:
            _proc_cache[pid] = p
            try:
                p.cpu_percent(None)  # Messung "primen"
            except Exception:
                pass

    # tote Prozesse aus dem Cache entfernen
    for pid in list(_proc_cache.keys()):
        if pid not in current_pids:
            _proc_cache.pop(pid, None)

    results = []
    for pid, proc in list(_proc_cache.items()):
        try:
            results.append({
                "pid": pid,
                "name": proc.name(),
                "cpu": round(proc.cpu_percent(None), 1),
                "mem": round(proc.memory_percent(), 1),
            })
        except Exception:
            continue

    results.sort(key=lambda x: x["cpu"], reverse=True)
    return results[:limit]


def listening_ports():
    """Liste aller lokal lauschenden TCP/UDP-Ports — praktisch um zu sehen,
    welche Dev-Server (Vite, Flask, Node, Docker, ...) gerade aktiv sind."""
    if psutil is None:
        return []
    results = []
    try:
        conns = psutil.net_connections(kind="inet")
    except Exception:
        return results

    seen_ports = set()
    for c in conns:
        if c.status == psutil.CONN_LISTEN and c.laddr:
            port = c.laddr.port
            if port in seen_ports:
                continue
            seen_ports.add(port)
            pname = "?"
            if c.pid:
                try:
                    pname = psutil.Process(c.pid).name()
                except Exception:
                    pass
            results.append({"port": port, "pid": c.pid, "process": pname})

    results.sort(key=lambda x: x["port"])
    return results


def uptime_seconds(boot_time):
    if not boot_time:
        return None
    return max(0, time.time() - boot_time)
