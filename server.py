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
    GET  /api/notes           -> gespeicherte Schnellnotizen
    POST /api/notes           -> Schnellnotizen speichern
    GET  /api/config          -> aktuelle Konfiguration (u.a. Sprache)
    POST /api/config          -> Konfiguration aendern (persistiert in config.json)
    POST /api/launch          -> Quick-Launch-Befehl ausfuehren
    POST /api/terminal        -> oeffnet zusaetzlich ein eigenstaendiges Shell-Fenster

  WebSocket (Namespace /pty):
    Verbindet xterm.js im Browser mit einer echten Shell (PowerShell/bash)
    ueber eine PTY-Bridge -> vollstaendig eingebettetes, interaktives Terminal.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from flask_socketio import SocketIO

sys.path.insert(0, str(Path(__file__).resolve().parent))
from helpers import system_info, git_tools, pty_bridge  # noqa: E402

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
REPOS_FILE = BASE_DIR / "repos.json"
CONFIG_FILE = BASE_DIR / "config.json"
NOTES_FILE = BASE_DIR / "notes.txt"

IS_WINDOWS = sys.platform == "win32"

DEFAULT_CONFIG = {
    "language": "de",
    "shell_windows": "powershell.exe",
    "shell_unix": "bash",
    "quick_launch": [
        {"label": "VS Code", "command": "code ."},
        {"label": "Explorer", "command": "explorer.exe ." if IS_WINDOWS else "xdg-open ."},
    ],
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
            return {**DEFAULT_CONFIG, **cfg}
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
    return jsonify({
        "server_time": time.time(),
        "local_ip": system_info.get_local_ip(),
        "public": system_info.get_public_ip_and_geo(),
        "system": system_info.get_system_stats(),
    })


@app.route("/api/processes")
def api_processes():
    return jsonify(system_info.top_processes())


@app.route("/api/ports")
def api_ports():
    return jsonify(system_info.listening_ports())


# ---------------------------------------------------------------------------
# Git-Repos
# ---------------------------------------------------------------------------

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
        results.append(info)
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
    cfg = load_config()
    cfg.update(data)
    save_config(cfg)
    return jsonify(cfg)


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
    print(" DEVHUB Cyber Command Center v2")
    print(" http://127.0.0.1:5050")
    print("=" * 60)
    # allow_unsafe_werkzeug: unbedenklich hier, da DEVHUB ausschliesslich an
    # 127.0.0.1 bindet (nur lokaler Single-User-Zugriff, kein oeffentlicher Server).
    socketio.run(app, host="127.0.0.1", port=5050, debug=False, allow_unsafe_werkzeug=True)
