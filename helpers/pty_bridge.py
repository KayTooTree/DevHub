"""
pty_bridge.py — Verwaltet echte, interaktive Shell-Sessions fuer das
eingebettete Browser-Terminal (xterm.js <-> WebSocket <-> echte PTY).

Architektur (wie bei Wetty / ttyd / edex-ui):
  1. Browser oeffnet eine Socket.IO-Verbindung im Namespace "/pty".
  2. Fuer jede Verbindung wird ein echter Shell-Prozess (PowerShell/bash)
     an eine Pseudo-Terminal-Instanz gebunden gestartet.
  3. Ein Hintergrund-Thread liest den Output der Shell und schickt ihn per
     "pty-output"-Event an genau diesen Client.
  4. Tastatureingaben aus xterm.js kommen per "pty-input"-Event zurueck und
     werden 1:1 in die Shell geschrieben — der Nutzer tippt also direkt in
     eine echte PowerShell/Bash, nicht in eine Simulation.

Windows nutzt `pywinpty` (ConPTY-Wrapper), Unix nutzt `ptyprocess`.
Beide Pakete bieten absichtlich eine (fast) identische API, dadurch
funktioniert dieser Code plattformunabhaengig ohne if/else-Huelle rund um
jeden einzelnen Aufruf.
"""

import sys
import threading

IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    from winpty import PtyProcess
else:
    from ptyprocess import PtyProcess

_sessions = {}       # session_id -> PtyProcess
_lock = threading.Lock()


def default_shell():
    return "powershell.exe" if IS_WINDOWS else "bash"


def start_session(session_id, socketio, shell_cmd=None, cols=120, rows=30):
    """Startet eine neue PTY-Session + Reader-Thread fuer eine Client-Verbindung."""
    shell_cmd = shell_cmd or default_shell()

    with _lock:
        if session_id in _sessions:
            return

        try:
            proc = PtyProcess.spawn([shell_cmd], dimensions=(rows, cols))
        except Exception as e:
            socketio.emit(
                "pty-output",
                f"\r\n[DEVHUB] Konnte Shell '{shell_cmd}' nicht starten: {e}\r\n"
                f"[DEVHUB] Ist die Shell installiert und im PATH? Siehe config.json.\r\n",
                room=session_id,
                namespace="/pty",
            )
            return

        _sessions[session_id] = proc

    def _reader():
        while True:
            try:
                if not proc.isalive():
                    break
                data = proc.read(4096)
                if not data:
                    break
                if isinstance(data, bytes):
                    data = data.decode("utf-8", errors="replace")
                socketio.emit("pty-output", data, room=session_id, namespace="/pty")
            except EOFError:
                break
            except Exception:
                break
        socketio.emit(
            "pty-output",
            "\r\n[DEVHUB] Sitzung beendet.\r\n",
            room=session_id,
            namespace="/pty",
        )
        with _lock:
            _sessions.pop(session_id, None)

    threading.Thread(target=_reader, daemon=True).start()


def write_to_session(session_id, data):
    proc = _sessions.get(session_id)
    if proc and proc.isalive():
        try:
            # pywinpty (Windows) nimmt str entgegen, ptyprocess (Unix) verlangt
            # zwingend bytes -- das ist ein tatsaechlicher API-Unterschied
            # zwischen den beiden Paketen, kein Bug.
            if IS_WINDOWS:
                proc.write(data)
            else:
                proc.write(data.encode("utf-8", errors="replace"))
        except Exception:
            pass


def resize_session(session_id, cols, rows):
    proc = _sessions.get(session_id)
    if proc and proc.isalive():
        try:
            proc.setwinsize(rows, cols)
        except Exception:
            pass


def end_session(session_id):
    with _lock:
        proc = _sessions.pop(session_id, None)
    if proc:
        try:
            proc.terminate(force=True)
        except Exception:
            pass


def active_session_count():
    return len(_sessions)
