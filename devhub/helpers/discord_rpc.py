"""
discord_rpc.py — Discord Rich Presence fuer DEVHUB.

Zeigt im Discord-Profil an, dass DevHub laeuft: standardmaessig
"Powered by DevHub" + ein Link-Button zum Repo/zur Homepage, optional mit
Live-Status aus dem Dashboard (z.B. "2 Repos hinter Remote").

Verbindet sich per lokalem IPC mit dem auf demselben Rechner laufenden
Discord-Client (das ist das normale Funktionsprinzip von Discord Rich
Presence -- es gibt keinen Server, an den Daten geschickt werden muessen).

Faellt komplett unauffaellig weg, wenn:
- 'pypresence' nicht installiert ist
- Discord nicht laeuft
- kein client_id konfiguriert ist
In all diesen Faellen laeuft DevHub normal weiter, nur ohne RPC-Anzeige.
"""

import threading
import time

try:
    from pypresence import Presence
except ImportError:
    Presence = None

# Der Link-Button ist bewusst fest verankert (nicht ueber config.json
# konfigurierbar) -- alles andere (Text, Live-Status, Bild) laesst sich im
# DevHub Dashboard ueber das Zahnrad-Symbol einstellen.
DEVHUB_BUTTON_LABEL = "View DevHub"
DEVHUB_BUTTON_URL = "https://github.com/KayTooTree/DevHub.git"

_lock = threading.Lock()
_client = None
_current_client_id = None
_stop_flag = False
_start_ts = int(time.time())

_state = {
    "available": Presence is not None,
    "enabled": False,
    "connected": False,
    "last_error": None,
}


def get_status():
    with _lock:
        return dict(_state)


def _set_state(**kwargs):
    with _lock:
        _state.update(kwargs)


def _disconnect():
    global _client, _current_client_id
    try:
        if _client:
            _client.close()
    except Exception:
        pass
    _client = None
    _current_client_id = None


def _ensure_connected(client_id):
    global _client, _current_client_id
    if _client is not None and _current_client_id == client_id:
        return  # schon verbunden mit dem richtigen Client
    _disconnect()
    _client = Presence(client_id)
    _client.connect()
    _current_client_id = client_id


def _push_update(cfg, live_state_text):
    details = (cfg.get("details") or "Powered by DevHub").strip() or "Powered by DevHub"

    if cfg.get("show_live_status", True) and live_state_text:
        state_text = live_state_text
    else:
        state_text = (cfg.get("state") or "").strip()

    kwargs = {"details": details, "start": _start_ts}
    if state_text:
        kwargs["state"] = state_text

    # Fest verankert -- immer der DevHub-GitHub-Link, unabhaengig von der Config.
    kwargs["buttons"] = [{"label": DEVHUB_BUTTON_LABEL, "url": DEVHUB_BUTTON_URL}]

    if cfg.get("large_image_key"):
        kwargs["large_image"] = cfg["large_image_key"]
        if cfg.get("large_image_text"):
            kwargs["large_text"] = cfg["large_image_text"]

    _client.update(**kwargs)


def run_loop(get_config_fn, live_state_fn=None, poll_interval=15):
    """Laeuft dauerhaft in einem Hintergrund-Thread (daemon). get_config_fn()
    wird bei jedem Durchlauf neu aufgerufen, damit Config-Aenderungen ohne
    Neustart des Servers wirksam werden."""
    global _stop_flag

    if Presence is None:
        _set_state(available=False, last_error="Python-Paket 'pypresence' fehlt")
        return

    while not _stop_flag:
        cfg = get_config_fn() or {}
        enabled = bool(cfg.get("enabled")) and bool(cfg.get("client_id"))
        _set_state(enabled=enabled)

        if not enabled:
            if _client is not None:
                _disconnect()
            _set_state(connected=False, last_error=None)
            time.sleep(poll_interval)
            continue

        try:
            _ensure_connected(cfg["client_id"])
            live_text = live_state_fn() if live_state_fn else ""
            _push_update(cfg, live_text)
            _set_state(connected=True, last_error=None)
        except Exception as e:
            _disconnect()
            _set_state(connected=False, last_error=str(e))

        time.sleep(poll_interval)


def stop():
    global _stop_flag
    _stop_flag = True
    _disconnect()
