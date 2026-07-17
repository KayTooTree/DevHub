"""
system_info.py — Server-Metriken fuer den DEVHUB Agent.

Bewusst schlanker als das Client-Pendant: kein Public-IP/Geolocation-Lookup
(ein Server kennt seinen Standort selbst und muss dafuer keine externe API
bei jedem Poll aufrufen), kein Akkustatus (Server haben keinen Akku), kein
Ping (das macht der Client selbst gegen den Agent-Host).
"""

import getpass
import os
import platform
import socket
import time

try:
    import psutil
except ImportError:
    psutil = None

_proc_cache = {}


def get_hostname():
    try:
        return socket.gethostname()
    except Exception:
        return "UNKNOWN-HOST"


def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


def get_os_info():
    try:
        return f"{platform.system()} {platform.release()}"
    except Exception:
        return "unknown"


def get_agent_user():
    try:
        return getpass.getuser()
    except Exception:
        return os.environ.get("USER") or os.environ.get("USERNAME") or "unknown"


def get_system_stats():
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
    if psutil is None:
        return []

    current_pids = set()
    for p in psutil.process_iter(["pid"]):
        pid = p.info["pid"]
        current_pids.add(pid)
        if pid not in _proc_cache:
            _proc_cache[pid] = p
            try:
                p.cpu_percent(None)
            except Exception:
                pass

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
