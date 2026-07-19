"""
DEVHUB — Cyber Command Center (Server v2)

Lokaler Server auf Basis von Flask + Flask-SocketIO. Bindet an 127.0.0.1
(nicht von aussen erreichbar) und stellt bereit:

  REST-API:
    GET  /api/status          -> Zeit, CPU/RAM/Disk, lokale/oeffentliche IP
    GET  /api/repos           -> Git-Status aller konfigurierten Repos
    POST /api/repos/pull      -> git pull fuer ein Repo
    POST /api/repos/pull_all  -> git pull fuer alle Repos
    POST /api/repos/open      -> Repo in VS Code / Explorer oeffnen
    GET  /api/processes       -> Top-Prozesse nach CPU
    GET  /api/ports           -> lokal lauschende Ports
    GET  /api/connections     -> aktiv genutzte (ESTABLISHED) Verbindungen
    GET  /api/cheatsheet      -> kuratierte Befehlsreferenz (cheatsheet.json)
    GET  /api/notes           -> gespeicherte Schnellnotizen
    POST /api/notes           -> Schnellnotizen speichern
    GET  /api/config          -> aktuelle Konfiguration (u.a. Sprache)
    POST /api/config          -> Konfiguration aendern (persistiert in config.json)
    POST /api/launch          -> Quick-Launch-Befehl ausfuehren
    POST /api/terminal        -> oeffnet zusaetzlich ein eigenstaendiges Shell-Fenster
    GET  /api/discord/status  -> Verbindungsstatus der Discord Rich Presence
    GET  /api/telemetry/status    -> Verbindungsstatus des Heartbeats
    POST /api/telemetry/feedback  -> Feedback an den DevHub Bot senden

    POST /api/discord/link/start   -> generiert Verify-Code, startet Hintergrund-Polling
    GET  /api/discord/link/status  -> Status des laufenden/abgeschlossenen Verknuepfungsversuchs
    POST /api/discord/link/cancel  -> bricht laufende Verknuepfung ab
    POST /api/discord/unlink       -> trennt die verknuepfte Discord-Identitaet

    GET    /api/repos/config          -> rohe Repo-Konfiguration (kein git fetch, fuer Onboarding/Settings)
    POST   /api/repos/config          -> Repo hinzufuegen {name, path, github?}
    DELETE /api/repos/config/<name>   -> Repo entfernen

    GET  /api/servers                       -> Liste verlinkter Remote-Server (ohne Token)
    POST /api/servers                       -> Server hinzufuegen {name, host, port, token}
    DEL  /api/servers/<name>                -> Server entfernen
    GET  /api/servers/<name>/health          -> Erreichbarkeits-Check
    GET  /api/servers/<name>/status          -> Remote-Systemstatus
    GET  /api/servers/<name>/processes       -> Remote-Top-Prozesse
    GET  /api/servers/<name>/ports           -> Remote-offene-Ports
    GET  /api/servers/<name>/docker          -> Remote-Docker-Status
    GET  /api/servers/<name>/repos           -> Remote-Git-Status
    POST /api/servers/<name>/repos/pull      -> Remote git pull (ein Repo)
    POST /api/servers/<name>/repos/pull_all  -> Remote git pull (alle Repos)
    GET  /api/servers/<name>/notes           -> geteilte Notizen auf dem Server
    POST /api/servers/<name>/notes           -> Notiz an den Server senden
    GET  /api/servers/<name>/logs            -> Audit-Log des Servers

  WebSocket (Namespace /pty):
    Verbindet xterm.js im Browser mit einer echten Shell (PowerShell/bash)
    ueber eine PTY-Bridge -> vollstaendig eingebettetes, interaktives Terminal.
"""

import json
import os
import subprocess
import sys
import threading
import time
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from flask_socketio import SocketIO

sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import system_info, git_tools, pty_bridge, docker_tools, github_tools, remote_agent, discord_rpc, telemetry, discord_link  # noqa: E402

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
REPOS_FILE = BASE_DIR / "repos.json"
CONFIG_FILE = BASE_DIR / "config.json"
NOTES_FILE = BASE_DIR / "notes.txt"
SERVERS_FILE = BASE_DIR / "servers.json"
CHEATSHEET_FILE = BASE_DIR / "cheatsheet.json"

IS_WINDOWS = sys.platform == "win32"

DEFAULT_CONFIG = {
    "language": "de",
    "shell_windows": "powershell.exe",
    "shell_unix": "bash",
    "ping_host": "8.8.8.8",
    "operator_name": "",
    "onboarding_complete": False,
    "quick_launch": [
        {"label": "VS Code", "command": "code ."},
        {"label": "Explorer", "command": "explorer.exe ." if IS_WINDOWS else "xdg-open ."},
    ],
    "discord_rpc": {
        "enabled": True,
        "client_id": "",
        "show_live_status": True,
        "details": "Powered by DevHub",
        "state": "",
        "large_image_key": "",
        "large_image_text": "",
    },
    "telemetry": {
        "enabled": True,
        "instance_id": "",
        "server_addr_url": "",
        "secret": "",
    },
    "discord_identity": None,
}

app = Flask(__name__, static_folder=None)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")


# ---------------------------------------------------------------------------
# Config-Handling
# ---------------------------------------------------------------------------

def load_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            merged = {**DEFAULT_CONFIG, **cfg}
            # discord_rpc ist verschachtelt -- fehlende Unterfelder (z.B. nach
            # einem Update) sollen aus den Defaults aufgefuellt werden, statt
            # den ganzen Block zu verlieren.
            merged["discord_rpc"] = {**DEFAULT_CONFIG["discord_rpc"], **cfg.get("discord_rpc", {})}
            merged["telemetry"] = {**DEFAULT_CONFIG["telemetry"], **cfg.get("telemetry", {})}
            return merged
        except Exception:
            return dict(DEFAULT_CONFIG)
    return dict(DEFAULT_CONFIG)


def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Static frontend
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.route("/static/<path:filename>")
def static_files(filename):
    return send_from_directory(STATIC_DIR, filename)


# ---------------------------------------------------------------------------
# System / Netzwerk
# ---------------------------------------------------------------------------

@app.route("/api/status")
def api_status():
    cfg = load_config()
    identity = cfg.get("discord_identity")
    return jsonify({
        "server_time": time.time(),
        "local_ip": system_info.get_local_ip(),
        "public": system_info.get_public_ip_and_geo(),
        "system": system_info.get_system_stats(),
        "username": system_info.get_username(),
        "hostname": system_info.get_hostname(),
        "battery": system_info.get_battery(),
        "operator_name": get_operator_name(),
        "discord_avatar": identity.get("avatar_url") if identity else None,
    })


@app.route("/api/ping")
def api_ping():
    cfg = load_config()
    ms = system_info.ping_latency(cfg.get("ping_host", "8.8.8.8"))
    return jsonify({"ms": ms})


@app.route("/api/processes")
def api_processes():
    return jsonify(system_info.top_processes())


@app.route("/api/ports")
def api_ports():
    return jsonify(system_info.listening_ports())


@app.route("/api/connections")
def api_connections():
    return jsonify(system_info.active_connections())


@app.route("/api/cheatsheet")
def api_cheatsheet():
    """Liest cheatsheet.json -- Nutzer koennen die Datei direkt erweitern,
    kein Editor-UI noetig fuer dieses Feature."""
    if not CHEATSHEET_FILE.exists():
        return jsonify([])
    try:
        with open(CHEATSHEET_FILE, "r", encoding="utf-8") as f:
            return jsonify(json.load(f))
    except Exception:
        return jsonify([])


@app.route("/api/docker")
def api_docker():
    return jsonify(docker_tools.docker_status())


# ---------------------------------------------------------------------------
# Git-Repos
# ---------------------------------------------------------------------------

_repo_status_cache = {"ts": 0, "behind": 0}


@app.route("/api/repos/config", methods=["GET"])
def api_repos_config_list():
    """Rohe Repo-Konfiguration (kein git fetch, keine Wartezeit) --
    fuer Onboarding/Settings, wo nur Name/Pfad verwaltet werden."""
    return jsonify(git_tools.load_repos(REPOS_FILE))


@app.route("/api/repos/config", methods=["POST"])
def api_repos_config_add():
    data = request.get_json(force=True)
    name = (data.get("name") or "").strip()
    path = (data.get("path") or "").strip()
    github = (data.get("github") or "").strip()
    if not name or not path:
        return jsonify({"ok": False, "error": "name und path sind erforderlich"}), 400

    repos = git_tools.load_repos(REPOS_FILE)
    if any(r.get("name") == name for r in repos):
        return jsonify({"ok": False, "error": "Ein Repo mit diesem Namen existiert bereits"}), 400

    entry = {"name": name, "path": path}
    if github:
        entry["github"] = github
    repos.append(entry)
    git_tools.save_repos(REPOS_FILE, repos)
    return jsonify({"ok": True, "repos": repos})


@app.route("/api/repos/config/<name>", methods=["DELETE"])
def api_repos_config_delete(name):
    repos = git_tools.load_repos(REPOS_FILE)
    new_repos = [r for r in repos if r.get("name") != name]
    if len(new_repos) == len(repos):
        return jsonify({"ok": False, "error": "Repo nicht gefunden"}), 404
    git_tools.save_repos(REPOS_FILE, new_repos)
    return jsonify({"ok": True, "repos": new_repos})


@app.route("/api/repos")
def api_repos():
    repos = git_tools.load_repos(REPOS_FILE)
    results = []
    for repo in repos:
        name = repo.get("name", repo.get("path", "unknown"))
        path = repo.get("path")
        info = git_tools.check_repo_status(path)
        info["name"] = name
        info["path"] = path
        github_slug = repo.get("github")
        if github_slug:
            info["github_stats"] = github_tools.get_repo_stats(github_slug)
        results.append(info)

    _repo_status_cache["ts"] = time.time()
    _repo_status_cache["behind"] = sum(
        1 for r in results if r.get("status") in ("BEHIND", "DIVERGED")
    )
    return jsonify(results)


@app.route("/api/repos/pull", methods=["POST"])
def api_repo_pull():
    data = request.get_json(force=True)
    path = data.get("path")
    if not path:
        return jsonify({"ok": False, "error": "kein path angegeben"}), 400
    return jsonify(git_tools.pull(path))


@app.route("/api/repos/pull_all", methods=["POST"])
def api_repo_pull_all():
    repos = git_tools.load_repos(REPOS_FILE)
    results = []
    for repo in repos:
        path = repo.get("path")
        name = repo.get("name", path)
        r = git_tools.pull(path)
        r["name"] = name
        results.append(r)
    return jsonify(results)


@app.route("/api/repos/open", methods=["POST"])
def api_repo_open():
    data = request.get_json(force=True)
    return jsonify(git_tools.open_in_tool(data.get("path"), data.get("tool")))


# ---------------------------------------------------------------------------
# Notizen
# ---------------------------------------------------------------------------

@app.route("/api/notes", methods=["GET"])
def api_get_notes():
    if NOTES_FILE.exists():
        return jsonify({"text": NOTES_FILE.read_text(encoding="utf-8")})
    return jsonify({"text": ""})


@app.route("/api/notes", methods=["POST"])
def api_save_notes():
    data = request.get_json(force=True)
    NOTES_FILE.write_text(data.get("text", ""), encoding="utf-8")
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Konfiguration (u.a. Sprache DE/EN)
# ---------------------------------------------------------------------------

@app.route("/api/config", methods=["GET"])
def api_get_config():
    return jsonify(load_config())


@app.route("/api/config", methods=["POST"])
def api_set_config():
    data = request.get_json(force=True)
    # button_label/button_url sind absichtlich nicht mehr Teil des Schemas --
    # der Discord-Link-Button ist fest im Code verankert (discord_rpc.py).
    # Falls jemand diese Felder trotzdem mitschickt, werden sie ignoriert
    # statt wirkungslos in config.json zu landen.
    if isinstance(data.get("discord_rpc"), dict):
        data["discord_rpc"].pop("button_label", None)
        data["discord_rpc"].pop("button_url", None)
    cfg = load_config()
    cfg.update(data)
    save_config(cfg)
    return jsonify(cfg)


# ---------------------------------------------------------------------------
# Discord Rich Presence
# ---------------------------------------------------------------------------

def get_live_state_text():
    """Kurzer Live-Status fuer die Discord Rich Presence, z.B. '2 Repos
    hinter Remote · 1 Terminal-Session'. Nutzt den Repo-Cache aus
    /api/repos statt selbst neue git-fetches auszuloesen (der Cache wird
    nur aktualisiert, wenn das Dashboard sowieso gerade offen/aktiv ist)."""
    parts = []
    if time.time() - _repo_status_cache["ts"] < 120 and _repo_status_cache["behind"]:
        parts.append(f"{_repo_status_cache['behind']} repo(s) behind")
    term_count = pty_bridge.active_session_count()
    if term_count:
        parts.append(f"{term_count} terminal session(s)")
    return " · ".join(parts) if parts else "Dashboard active"


@app.route("/api/discord/status")
def api_discord_status():
    return jsonify(discord_rpc.get_status())


@app.route("/api/telemetry/status")
def api_telemetry_status():
    return jsonify(telemetry.get_status())


@app.route("/api/telemetry/feedback", methods=["POST"])
def api_telemetry_feedback():
    data = request.get_json(force=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"ok": False, "error": "leerer Text"}), 400
    cfg = load_config()
    ok, err = telemetry.send_feedback(cfg, text)
    return jsonify({"ok": ok, "error": err})


# ---------------------------------------------------------------------------
# Discord-Account-Verknuepfung
# ---------------------------------------------------------------------------

_link_state = {"code": None, "waiting": False, "linked": False, "identity": None, "error": None}
_link_lock = threading.Lock()
_link_cancel_flag = {"cancel": False}


def _run_link_poll(code):
    cfg = load_config()
    identity, err = discord_link.poll_claim(cfg, code, stop_check=lambda: _link_cancel_flag["cancel"])
    with _link_lock:
        if _link_cancel_flag["cancel"]:
            _link_state.update(waiting=False)
            return
        if identity:
            fresh_cfg = load_config()
            saved = discord_link.save_identity(fresh_cfg, save_config, identity)
            _link_state.update(waiting=False, linked=True, identity=saved, error=None)
        else:
            _link_state.update(waiting=False, linked=False, error=err)


@app.route("/api/discord/link/start", methods=["POST"])
def api_discord_link_start():
    code = discord_link.generate_code()
    with _link_lock:
        _link_cancel_flag["cancel"] = False
        _link_state.update(code=code, waiting=True, linked=False, identity=None, error=None)
    threading.Thread(target=_run_link_poll, args=(code,), daemon=True).start()
    return jsonify({"code": code})


@app.route("/api/discord/link/status")
def api_discord_link_status():
    with _link_lock:
        return jsonify(dict(_link_state))


@app.route("/api/discord/link/cancel", methods=["POST"])
def api_discord_link_cancel():
    with _link_lock:
        _link_cancel_flag["cancel"] = True
        _link_state.update(waiting=False)
    return jsonify({"ok": True})


@app.route("/api/discord/unlink", methods=["POST"])
def api_discord_unlink():
    cfg = load_config()
    discord_link.clear_identity(cfg, save_config)
    with _link_lock:
        _link_state.update(code=None, waiting=False, linked=False, identity=None, error=None)
    return jsonify({"ok": True})


# ---------------------------------------------------------------------------
# Quick-Launch & externes Terminal-Fenster
# ---------------------------------------------------------------------------

@app.route("/api/launch", methods=["POST"])
def api_launch():
    data = request.get_json(force=True)
    idx = data.get("index")
    cfg = load_config()
    items = cfg.get("quick_launch", [])
    if idx is None or not (0 <= idx < len(items)):
        return jsonify({"ok": False, "error": "invalid index"}), 400
    cmd = items[idx].get("command")
    try:
        subprocess.Popen(cmd, shell=True)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/terminal", methods=["POST"])
def api_terminal():
    """Oeffnet zusaetzlich ein eigenstaendiges Shell-Fenster (Fallback,
    falls das eingebettete Terminal mal nicht starten sollte)."""
    try:
        if IS_WINDOWS:
            subprocess.Popen(["powershell.exe", "-NoExit"],
                              creationflags=subprocess.CREATE_NEW_CONSOLE)
        elif sys.platform == "darwin":
            subprocess.Popen(["open", "-a", "Terminal"])
        else:
            subprocess.Popen(["x-terminal-emulator"])
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


# ---------------------------------------------------------------------------
# Remote Servers (DEVHUB Agents auf verlinkten Servern)
#
# Der API-Key jedes Servers steht NUR in servers.json auf dieser Maschine
# und wird niemals an den Browser geschickt -- alle Aufrufe laufen
# server-seitig (Python -> Python, kein CORS) ueber helpers/remote_agent.py.
# ---------------------------------------------------------------------------

def load_servers():
    if not SERVERS_FILE.exists():
        return []
    try:
        with open(SERVERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_servers(servers):
    with open(SERVERS_FILE, "w", encoding="utf-8") as f:
        json.dump(servers, f, indent=2, ensure_ascii=False)


def get_operator_name():
    """Der Name, der bei Remote-Aktionen im Audit-Log des Agents landet.
    Bevorzugt den verknuepften Discord-Anzeigenamen, faellt sonst auf den
    manuell gesetzten Namen bzw. den lokalen OS-Benutzernamen zurueck."""
    cfg = load_config()
    identity = cfg.get("discord_identity")
    if identity and identity.get("display_name"):
        return identity["display_name"]
    return cfg.get("operator_name") or system_info.get_username()


def find_server(name):
    for s in load_servers():
        if s.get("name") == name:
            return s
    return None


def public_server(s):
    """Server-Objekt OHNE Token fuers Frontend (Karten/Listen-Ansicht)."""
    return {"name": s.get("name"), "host": s.get("host"), "port": s.get("port")}


@app.route("/api/servers", methods=["GET"])
def api_list_servers():
    return jsonify([public_server(s) for s in load_servers()])


@app.route("/api/servers", methods=["POST"])
def api_add_server():
    data = request.get_json(force=True)
    name = (data.get("name") or "").strip()
    host = (data.get("host") or "").strip()
    port = data.get("port")
    token = (data.get("token") or "").strip()
    if not name or not host or not port or not token:
        return jsonify({"ok": False, "error": "name, host, port und token sind erforderlich"}), 400

    servers = load_servers()
    if any(s.get("name") == name for s in servers):
        return jsonify({"ok": False, "error": "Ein Server mit diesem Namen existiert bereits"}), 400

    servers.append({"name": name, "host": host, "port": int(port), "token": token})
    save_servers(servers)
    return jsonify({"ok": True})


@app.route("/api/servers/<name>", methods=["DELETE"])
def api_delete_server(name):
    servers = load_servers()
    new_servers = [s for s in servers if s.get("name") != name]
    if len(new_servers) == len(servers):
        return jsonify({"ok": False, "error": "Server nicht gefunden"}), 404
    save_servers(new_servers)
    return jsonify({"ok": True})


@app.route("/api/servers/<name>/health")
def api_server_health(name):
    server = find_server(name)
    if not server:
        return jsonify({"online": False, "error": "unbekannter Server"}), 404
    return jsonify(remote_agent.check_health(server))


@app.route("/api/servers/<name>/status")
def api_server_status(name):
    server = find_server(name)
    if not server:
        return jsonify({"error": "unbekannter Server"}), 404
    return jsonify(remote_agent.get_status(server))


@app.route("/api/servers/<name>/processes")
def api_server_processes(name):
    server = find_server(name)
    if not server:
        return jsonify({"error": "unbekannter Server"}), 404
    return jsonify(remote_agent.get_processes(server))


@app.route("/api/servers/<name>/ports")
def api_server_ports(name):
    server = find_server(name)
    if not server:
        return jsonify({"error": "unbekannter Server"}), 404
    return jsonify(remote_agent.get_ports(server))


@app.route("/api/servers/<name>/docker")
def api_server_docker(name):
    server = find_server(name)
    if not server:
        return jsonify({"error": "unbekannter Server"}), 404
    return jsonify(remote_agent.get_docker(server))


@app.route("/api/servers/<name>/repos")
def api_server_repos(name):
    server = find_server(name)
    if not server:
        return jsonify({"error": "unbekannter Server"}), 404
    return jsonify(remote_agent.get_repos(server))


@app.route("/api/servers/<name>/repos/pull", methods=["POST"])
def api_server_repo_pull(name):
    server = find_server(name)
    if not server:
        return jsonify({"error": "unbekannter Server"}), 404
    data = request.get_json(force=True) or {}
    path = data.get("path")
    if not path:
        return jsonify({"error": "kein path angegeben"}), 400
    return jsonify(remote_agent.pull_repo(server, path, get_operator_name()))


@app.route("/api/servers/<name>/repos/pull_all", methods=["POST"])
def api_server_repo_pull_all(name):
    server = find_server(name)
    if not server:
        return jsonify({"error": "unbekannter Server"}), 404
    return jsonify(remote_agent.pull_all_repos(server, get_operator_name()))


@app.route("/api/servers/<name>/notes", methods=["GET"])
def api_server_notes_get(name):
    server = find_server(name)
    if not server:
        return jsonify({"error": "unbekannter Server"}), 404
    return jsonify(remote_agent.get_notes(server))


@app.route("/api/servers/<name>/notes", methods=["POST"])
def api_server_notes_post(name):
    server = find_server(name)
    if not server:
        return jsonify({"error": "unbekannter Server"}), 404
    data = request.get_json(force=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "leerer Text"}), 400
    return jsonify(remote_agent.add_note(server, text, get_operator_name()))


@app.route("/api/servers/<name>/logs")
def api_server_logs(name):
    server = find_server(name)
    if not server:
        return jsonify({"error": "unbekannter Server"}), 404
    return jsonify(remote_agent.get_logs(server))


# ---------------------------------------------------------------------------
# Eingebettetes Terminal (Socket.IO Namespace /pty)
# ---------------------------------------------------------------------------

@socketio.on("connect", namespace="/pty")
def pty_connect():
    sid = request.sid
    cfg = load_config()
    shell_cmd = cfg.get("shell_windows") if IS_WINDOWS else cfg.get("shell_unix")
    pty_bridge.start_session(sid, socketio, shell_cmd=shell_cmd)


@socketio.on("pty-input", namespace="/pty")
def pty_input(data):
    pty_bridge.write_to_session(request.sid, data)


@socketio.on("resize", namespace="/pty")
def pty_resize(dims):
    try:
        cols = int(dims.get("cols", 120))
        rows = int(dims.get("rows", 30))
    except Exception:
        cols, rows = 120, 30
    pty_bridge.resize_session(request.sid, cols, rows)


@socketio.on("disconnect", namespace="/pty")
def pty_disconnect():
    pty_bridge.end_session(request.sid)


if __name__ == "__main__":
    print("=" * 60)
    print(" DEVHUB Cyber Command Center v3")
    print(" http://127.0.0.1:5050")
    print("=" * 60)

    rpc_thread = threading.Thread(
        target=discord_rpc.run_loop,
        args=(lambda: load_config().get("discord_rpc", {}), get_live_state_text),
        daemon=True,
    )
    rpc_thread.start()

    telemetry_thread = threading.Thread(
        target=telemetry.run_loop,
        args=(load_config, save_config),
        daemon=True,
    )
    telemetry_thread.start()

    # allow_unsafe_werkzeug: unbedenklich hier, da DEVHUB ausschliesslich an
    # 127.0.0.1 bindet (nur lokaler Single-User-Zugriff, kein oeffentlicher Server).
    socketio.run(app, host="127.0.0.1", port=5050, debug=False, allow_unsafe_werkzeug=True)
