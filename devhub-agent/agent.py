"""
DEVHUB Agent — laeuft AUF einem Server und stellt eine authentifizierte
REST-API bereit, damit dein DEVHUB Client (auf deinem eigenen PC) diesen
Server im Dashboard anzeigen, Git-Repos pullen und geteilte Notizen mit
ihm austauschen kann.

============================== SICHERHEIT ==============================
1. JEDE Route (ausser /health) verlangt einen gueltigen API-Key im Header
   "Authorization: Bearer <key>". Der Key wird beim allerersten Start
   automatisch generiert und in agent_config.json gespeichert -- kopiere
   ihn von dort in die remote_servers-Konfiguration deines Clients.
2. Der Agent fuehrt NIEMALS beliebige Befehle aus. Es gibt keine
   "run arbitrary command"-Route und kein Terminal. Die einzige Aktion mit
   Seiteneffekt ist "git pull" -- und zwar ausschliesslich fuer Pfade, die
   explizit in repos.json auf DIESEM Server eingetragen sind (Whitelist).
3. Der Agent bindet standardmaessig an 0.0.0.0, damit er im Netzwerk
   erreichbar ist. Das heisst: JEDER im gleichen Netz kann Anfragen an ihn
   schicken (auch wenn ungueltige Keys immer abgelehnt werden). Nutze eine
   Firewall-Regel, ein VPN (Tailscale/WireGuard) oder SSH-Port-Forwarding,
   damit der Port NICHT direkt im offenen Internet haengt.
4. Nach mehreren fehlgeschlagenen Auth-Versuchen von derselben IP wird
   diese IP fuer eine Weile temporaer gesperrt (Brute-Force-Throttling).
==========================================================================
"""

import json
import secrets
import sys
import time
from functools import wraps
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import system_info, git_tools, docker_tools, audit_log  # noqa: E402

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
AGENT_CONFIG_FILE = BASE_DIR / "agent_config.json"
REPOS_FILE = BASE_DIR / "repos.json"
NOTES_FILE = BASE_DIR / "shared_notes.json"
AUDIT_LOG_FILE = BASE_DIR / "audit_log.jsonl"

DEFAULT_AGENT_CONFIG = {
    "name": "Mein Server",
    "api_key": "",
    "host": "0.0.0.0",
    "port": 8060,
    "rate_limit_max_attempts": 8,
    "rate_limit_window_seconds": 60,
    "rate_limit_block_seconds": 300,
}

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Konfiguration + Erstinstallation (API-Key generieren)
# ---------------------------------------------------------------------------

def load_agent_config():
    if AGENT_CONFIG_FILE.exists():
        try:
            with open(AGENT_CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            return {**DEFAULT_AGENT_CONFIG, **cfg}
        except Exception:
            return dict(DEFAULT_AGENT_CONFIG)
    return dict(DEFAULT_AGENT_CONFIG)


def save_agent_config(cfg):
    with open(AGENT_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def ensure_api_key():
    cfg = load_agent_config()
    if not cfg.get("api_key"):
        cfg["api_key"] = secrets.token_urlsafe(32)
        save_agent_config(cfg)
        print("=" * 70)
        print(" ERSTER START: neuer API-Key generiert.")
        print(" Trag diesen Key in die remote_servers-Konfiguration deines")
        print(" DEVHUB Clients ein (config.json):")
        print()
        print(f"   {cfg['api_key']}")
        print()
        print(" Der Key steht auch dauerhaft in agent_config.json.")
        print("=" * 70)
    return cfg


# ---------------------------------------------------------------------------
# Auth + einfaches Brute-Force-Throttling
# ---------------------------------------------------------------------------

_failed_attempts = {}   # ip -> [timestamps]
_blocked_until = {}     # ip -> unix_timestamp


def _client_ip():
    return request.headers.get("X-Forwarded-For", request.remote_addr) or "unknown"


def _is_blocked(ip):
    until = _blocked_until.get(ip)
    return bool(until and time.time() < until)


def _register_failure(ip, cfg):
    now = time.time()
    window = cfg.get("rate_limit_window_seconds", 60)
    attempts = [t for t in _failed_attempts.get(ip, []) if now - t < window]
    attempts.append(now)
    _failed_attempts[ip] = attempts
    if len(attempts) >= cfg.get("rate_limit_max_attempts", 8):
        _blocked_until[ip] = now + cfg.get("rate_limit_block_seconds", 300)


def require_auth(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        cfg = load_agent_config()
        ip = _client_ip()

        if _is_blocked(ip):
            return jsonify({"error": "Zu viele Fehlversuche, IP temporaer gesperrt"}), 429

        auth_header = request.headers.get("Authorization", "")
        token = auth_header[7:] if auth_header.startswith("Bearer ") else ""
        expected = cfg.get("api_key", "")

        if not token or not expected or not secrets.compare_digest(token, expected):
            _register_failure(ip, cfg)
            return jsonify({"error": "unauthorized"}), 401

        return f(*args, **kwargs)
    return wrapper


# ---------------------------------------------------------------------------
# Oeffentliche Health-Route (kein Auth noetig, fuer schnellen Erreichbarkeits-Check)
# ---------------------------------------------------------------------------

@app.route("/health")
def health():
    cfg = load_agent_config()
    return jsonify({"ok": True, "name": cfg.get("name", "DEVHUB Agent")})


# ---------------------------------------------------------------------------
# Server-Monitor-Panel ("Kuechenmonitor" -- zeigt Notizen/Status live an,
# unabhaengig davon ob gerade jemand den DEVHUB Client offen hat)
#
# Die HTML-Seite selbst braucht keinen Auth-Header (Browser koennen den
# schwer beim direkten Aufruf einer URL mitschicken). Die eigentlichen
# Daten-Endpunkte (/notes, /status, ...) bleiben ganz normal ueber
# require_auth geschuetzt -- das JS auf der Seite schickt den API-Key, den
# der Nutzer einmalig eintraegt (oder per #token=... in der URL mitgibt),
# in jedem fetch()-Aufruf als Authorization-Header mit.
# ---------------------------------------------------------------------------

@app.route("/panel")
def panel():
    return send_from_directory(STATIC_DIR, "panel.html")


@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory(STATIC_DIR, filename)


# ---------------------------------------------------------------------------
# Status / Metriken
# ---------------------------------------------------------------------------

@app.route("/status")
@require_auth
def status():
    return jsonify({
        "hostname": system_info.get_hostname(),
        "os": system_info.get_os_info(),
        "agent_user": system_info.get_agent_user(),
        "local_ip": system_info.get_local_ip(),
        "system": system_info.get_system_stats(),
        "server_time": time.time(),
    })


@app.route("/processes")
@require_auth
def processes():
    return jsonify(system_info.top_processes())


@app.route("/ports")
@require_auth
def ports():
    return jsonify(system_info.listening_ports())


@app.route("/docker")
@require_auth
def docker_status():
    return jsonify(docker_tools.docker_status())


# ---------------------------------------------------------------------------
# Git-Repos (nur Whitelist aus repos.json auf DIESEM Server)
# ---------------------------------------------------------------------------

@app.route("/repos")
@require_auth
def repos():
    repo_list = git_tools.load_repos(REPOS_FILE)
    results = []
    for repo in repo_list:
        path = repo.get("path")
        info = git_tools.check_repo_status(path)
        info["name"] = repo.get("name", path)
        info["path"] = path
        results.append(info)
    return jsonify(results)


@app.route("/repos/pull", methods=["POST"])
@require_auth
def repos_pull():
    data = request.get_json(force=True) or {}
    path = data.get("path")
    username = data.get("username", "unbekannt")
    allowed_paths = {r.get("path") for r in git_tools.load_repos(REPOS_FILE)}
    if path not in allowed_paths:
        return jsonify({"ok": False, "error": "Pfad nicht in repos.json whitelisted"}), 403
    result = git_tools.pull(path)
    audit_log.log_action(
        AUDIT_LOG_FILE, username, "PULL",
        f"{path} -> {'OK' if result['ok'] else 'FEHLER: ' + result.get('error', '')}"
    )
    return jsonify(result)


@app.route("/repos/pull_all", methods=["POST"])
@require_auth
def repos_pull_all():
    data = request.get_json(force=True) or {}
    username = data.get("username", "unbekannt")
    repo_list = git_tools.load_repos(REPOS_FILE)
    results = []
    for repo in repo_list:
        r = git_tools.pull(repo.get("path"))
        r["name"] = repo.get("name", repo.get("path"))
        results.append(r)
        audit_log.log_action(
            AUDIT_LOG_FILE, username, "PULL",
            f"{repo.get('path')} -> {'OK' if r['ok'] else 'FEHLER: ' + r.get('error', '')}"
        )
    return jsonify(results)


# ---------------------------------------------------------------------------
# Geteilte Notizen (fuer alle, die den API-Key dieses Servers haben)
# ---------------------------------------------------------------------------

MAX_NOTES = 200


def _load_notes():
    if not NOTES_FILE.exists():
        return []
    try:
        with open(NOTES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save_notes(notes):
    with open(NOTES_FILE, "w", encoding="utf-8") as f:
        json.dump(notes[-MAX_NOTES:], f, indent=2, ensure_ascii=False)


@app.route("/notes", methods=["GET"])
@require_auth
def get_notes():
    return jsonify(_load_notes())


@app.route("/notes", methods=["POST"])
@require_auth
def save_notes():
    data = request.get_json(force=True) or {}
    text = (data.get("text") or "").strip()
    username = data.get("username", "unbekannt")
    if not text:
        return jsonify({"ok": False, "error": "leerer Text"}), 400

    notes = _load_notes()
    entry = {"author": username, "text": text, "ts": time.time()}
    notes.append(entry)
    _save_notes(notes)
    audit_log.log_action(AUDIT_LOG_FILE, username, "NOTE", text[:120])
    return jsonify({"ok": True, "note": entry})


# ---------------------------------------------------------------------------
# Audit-Log (rein lesend -- wer hat wann was auf diesem Server gemacht)
# ---------------------------------------------------------------------------

@app.route("/logs")
@require_auth
def get_logs():
    return jsonify(audit_log.read_log(AUDIT_LOG_FILE))


if __name__ == "__main__":
    cfg = ensure_api_key()
    print("=" * 70)
    print(f" DEVHUB Agent — '{cfg.get('name')}'")
    print(f" Laeuft auf {cfg.get('host')}:{cfg.get('port')}")
    print(" Denk an Firewall/VPN, bevor du den Port oeffentlich freigibst!")
    print("=" * 70)
    app.run(host=cfg.get("host", "0.0.0.0"), port=cfg.get("port", 8060), debug=False)
