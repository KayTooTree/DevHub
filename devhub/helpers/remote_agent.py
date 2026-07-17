"""
remote_agent.py — Kommunikation des Clients mit entfernten DEVHUB-Agents
(auf verlinkten Servern). Laeuft komplett serverseitig im lokalen
Python-Backend des Clients -- der API-Key eines Agents wird NIE an den
Browser geschickt, nur die aufbereiteten Ergebnisse.
"""

import time

try:
    import requests
except ImportError:
    requests = None

REQUEST_TIMEOUT = 5
PULL_TIMEOUT = 65  # git pull kann laenger dauern als ein normaler Status-Call


def _base_url(server):
    return f"http://{server['host']}:{server['port']}"


def _headers(server):
    return {"Authorization": f"Bearer {server.get('token', '')}"}


def _get(server, path, timeout=REQUEST_TIMEOUT):
    if requests is None:
        return None, "Python-Paket 'requests' fehlt"
    try:
        r = requests.get(_base_url(server) + path, headers=_headers(server), timeout=timeout)
        if r.status_code == 401:
            return None, "Ungültiger API-Key"
        if r.status_code == 429:
            return None, "Agent hat diese Verbindung temporär gesperrt (zu viele Fehlversuche)"
        if r.status_code != 200:
            return None, f"HTTP {r.status_code}"
        return r.json(), None
    except requests.exceptions.ConnectTimeout:
        return None, "Zeitüberschreitung (Server offline oder falsche IP/Port?)"
    except requests.exceptions.ConnectionError:
        return None, "Keine Verbindung (Server offline, falsche IP/Port, oder Firewall?)"
    except Exception as e:
        return None, str(e)


def _post(server, path, payload, timeout=REQUEST_TIMEOUT):
    if requests is None:
        return None, "Python-Paket 'requests' fehlt"
    try:
        r = requests.post(_base_url(server) + path, headers=_headers(server), json=payload, timeout=timeout)
        if r.status_code == 401:
            return None, "Ungültiger API-Key"
        if r.status_code == 429:
            return None, "Agent hat diese Verbindung temporär gesperrt (zu viele Fehlversuche)"
        if r.status_code not in (200, 201):
            try:
                return r.json(), None  # z.B. 403 mit strukturierter Fehlermeldung (Whitelist-Verstoss)
            except Exception:
                return None, f"HTTP {r.status_code}"
        return r.json(), None
    except requests.exceptions.ConnectTimeout:
        return None, "Zeitüberschreitung (Server offline oder falsche IP/Port?)"
    except requests.exceptions.ConnectionError:
        return None, "Keine Verbindung (Server offline, falsche IP/Port, oder Firewall?)"
    except Exception as e:
        return None, str(e)


def check_health(server):
    """Schneller Erreichbarkeits-Check fuer die Server-Karte (online/offline)."""
    if requests is None:
        return {"online": False, "error": "requests fehlt"}
    try:
        r = requests.get(_base_url(server) + "/health", timeout=3)
        return {"online": r.status_code == 200}
    except Exception:
        return {"online": False}


def get_status(server):
    data, err = _get(server, "/status")
    return {"data": data, "error": err}


def get_processes(server):
    data, err = _get(server, "/processes")
    return {"data": data or [], "error": err}


def get_ports(server):
    data, err = _get(server, "/ports")
    return {"data": data or [], "error": err}


def get_docker(server):
    data, err = _get(server, "/docker")
    return {"data": data, "error": err}


def get_repos(server):
    data, err = _get(server, "/repos", timeout=20)
    return {"data": data or [], "error": err}


def pull_repo(server, path, username):
    data, err = _post(server, "/repos/pull", {"path": path, "username": username}, timeout=PULL_TIMEOUT)
    return {"data": data, "error": err}


def pull_all_repos(server, username):
    data, err = _post(server, "/repos/pull_all", {"username": username}, timeout=PULL_TIMEOUT)
    return {"data": data or [], "error": err}


def get_notes(server):
    data, err = _get(server, "/notes")
    return {"data": data or [], "error": err}


def add_note(server, text, username):
    data, err = _post(server, "/notes", {"text": text, "username": username})
    return {"data": data, "error": err}


def get_logs(server):
    data, err = _get(server, "/logs")
    return {"data": data or [], "error": err}
