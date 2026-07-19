"""
telemetry.py — Anonymer Heartbeat + Feedback-Versand an den DevHub Bot.

Funktionsprinzip:
  1. Beim Start (und danach stuendlich) wird server_addr.txt von einer
     oeffentlichen GitHub-Datei gelesen -- die aktuelle Adresse des
     DevHub-Bot-Telemetrie-Servers steht NICHT hart im Code, sondern kann
     durch einfaches Aendern dieser Datei im Repo umgezogen werden.
  2. Alle 10 Sekunden wird ein Heartbeat mit einer zufaelligen, lokal
     generierten instance_id geschickt -- das ist KEINE Discord- oder
     sonstige persoenliche Identitaet, nur ein anonymer Zaehler fuer
     "wie viele DevHub-Instanzen laufen gerade".
  3. Feedback (Freitext) kann optional darueber an den Bot geschickt
     werden, der es in einen Discord-Kanal postet.

Alles read-only/best-effort: schlaegt die Verbindung fehl (kein Internet,
Bot offline, Adresse falsch), laeuft DevHub normal weiter -- Telemetrie
ist nie ein Blocker fuer die eigentliche Nutzung.
"""

import threading
import time
import uuid

try:
    import requests
except ImportError:
    requests = None

DEFAULT_ADDR_URL = "https://raw.githubusercontent.com/KayTooTree/DevHub/main/server_addr.txt"
HEARTBEAT_INTERVAL_SECONDS = 10
ADDR_REFRESH_INTERVAL_SECONDS = 3600  # 1x pro Stunde neu nachschauen (falls Server umzieht)

_stop_flag = False
_state = {
    "enabled": False,
    "connected": False,
    "last_error": None,
    "resolved_addr": None,
}
_lock = threading.Lock()


def get_status():
    with _lock:
        return dict(_state)


def _set_state(**kwargs):
    with _lock:
        _state.update(kwargs)


def get_or_create_instance_id(cfg, save_config_fn):
    """Persistente, zufaellige Instanz-ID -- einmal generiert, dann in
    config.json gespeichert. Keine Discord-/Personenidentitaet."""
    telemetry_cfg = cfg.get("telemetry", {})
    instance_id = telemetry_cfg.get("instance_id")
    if not instance_id:
        instance_id = uuid.uuid4().hex
        telemetry_cfg["instance_id"] = instance_id
        cfg["telemetry"] = telemetry_cfg
        save_config_fn(cfg)
    return instance_id


def _fetch_server_addr(addr_url, timeout=5):
    if requests is None:
        return None
    try:
        r = requests.get(addr_url, timeout=timeout)
        if r.status_code == 200:
            addr = r.text.strip()
            return addr if addr else None
        return None
    except Exception:
        return None


def _send_heartbeat(base_url, secret, instance_id, timeout=5):
    if requests is None:
        return False, "requests fehlt"
    try:
        headers = {"X-DevHub-Secret": secret} if secret else {}
        r = requests.post(
            f"{base_url}/heartbeat", json={"instance_id": instance_id}, headers=headers, timeout=timeout
        )
        return r.status_code == 200, None if r.status_code == 200 else f"HTTP {r.status_code}"
    except Exception as e:
        return False, str(e)


def send_feedback(cfg, text, timeout=8):
    """Wird vom Feedback-Button im Dashboard aufgerufen. Gibt (ok, error) zurueck."""
    telemetry_cfg = cfg.get("telemetry", {})
    base_url = _state.get("resolved_addr")
    if not base_url:
        return False, "Kein Telemetrie-Server bekannt (noch nicht aufgeloest oder offline)"
    if requests is None:
        return False, "Python-Paket 'requests' fehlt"
    try:
        headers = {"X-DevHub-Secret": telemetry_cfg.get("secret", "")} if telemetry_cfg.get("secret") else {}
        r = requests.post(
            f"{base_url}/feedback",
            json={"instance_id": telemetry_cfg.get("instance_id", ""), "text": text},
            headers=headers,
            timeout=timeout,
        )
        if r.status_code != 200:
            return False, f"HTTP {r.status_code}"
        try:
            body = r.json()
        except Exception:
            body = {}
        if body.get("posted") is False:
            return False, "Bot hat keinen Feedback-Kanal konfiguriert (feedback_channel_id in der Bot-Config fehlt)"
        return True, None
    except Exception as e:
        return False, str(e)


def run_loop(get_config_fn, save_config_fn):
    """Hintergrund-Thread: loest server_addr.txt auf und schickt Heartbeats,
    solange telemetry.enabled in der Config wahr ist."""
    global _stop_flag
    last_addr_check = 0
    resolved_addr = None

    while not _stop_flag:
        cfg = get_config_fn() or {}
        telemetry_cfg = cfg.get("telemetry", {})
        enabled = telemetry_cfg.get("enabled", True)
        _set_state(enabled=enabled)

        if not enabled:
            _set_state(connected=False)
            time.sleep(HEARTBEAT_INTERVAL_SECONDS)
            continue

        addr_url = telemetry_cfg.get("server_addr_url") or DEFAULT_ADDR_URL
        now = time.time()
        if resolved_addr is None or (now - last_addr_check) > ADDR_REFRESH_INTERVAL_SECONDS:
            new_addr = _fetch_server_addr(addr_url)
            if new_addr:
                resolved_addr = new_addr.rstrip("/")
                _set_state(resolved_addr=resolved_addr)
            last_addr_check = now

        if not resolved_addr:
            _set_state(connected=False, last_error="server_addr.txt nicht erreichbar")
            time.sleep(HEARTBEAT_INTERVAL_SECONDS)
            continue

        instance_id = get_or_create_instance_id(cfg, save_config_fn)
        ok, err = _send_heartbeat(resolved_addr, telemetry_cfg.get("secret", ""), instance_id)
        _set_state(connected=ok, last_error=err)

        time.sleep(HEARTBEAT_INTERVAL_SECONDS)


def stop():
    global _stop_flag
    _stop_flag = True
