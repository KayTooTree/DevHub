"""
discord_link.py — Verknuepft den DevHub Client mit einer Discord-Identitaet.

Ablauf:
  1. generate_code() erzeugt einen zufaelligen, gut lesbaren Code
     (kein 0/O/1/I zur Vermeidung von Verwechslungen).
  2. Client zeigt den Code an, Nutzer tippt /verify <code> im Discord.
  3. poll_claim() fragt in Intervallen beim selben Telemetrie-Server nach,
     der auch fuer Heartbeat/Feedback genutzt wird (siehe telemetry.py) --
     kein zusaetzlicher offener Port noetig.

Sicherheitsmodell (bewusst leichtgewichtig, kein Banking-Grade-Auth):
Codes sind zufaellig, kurzlebig (5 Minuten) und Einmal-Nutzung
(Erst-Einloesung gewinnt). Das reicht fuer ein Community-/Dev-Tool.
"""

import secrets
import time

try:
    import requests
except ImportError:
    requests = None

from . import telemetry

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # ohne 0/O/1/I
CODE_LENGTH = 8
POLL_INTERVAL_SECONDS = 2
POLL_TIMEOUT_SECONDS = 300


def generate_code():
    return "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LENGTH))


def _telemetry_base_url(cfg):
    """Nutzt dieselbe aufgeloeste Adresse wie das Heartbeat-System."""
    status = telemetry.get_status()
    return status.get("resolved_addr")


def poll_claim(cfg, code, stop_check=None, timeout=POLL_TIMEOUT_SECONDS):
    """Blockierend (fuer einen Hintergrund-Thread gedacht) -- fragt
    wiederholt beim Bot nach, ob der Code eingeloest wurde.
    stop_check: optionale Funktion, die True zurueckgibt, wenn abgebrochen
    werden soll (z.B. Nutzer hat das Wizard-Fenster geschlossen)."""
    if requests is None:
        return None, "Python-Paket 'requests' fehlt"

    telemetry_cfg = cfg.get("telemetry", {})
    secret = telemetry_cfg.get("secret", "")
    deadline = time.time() + timeout

    while time.time() < deadline:
        if stop_check and stop_check():
            return None, "abgebrochen"

        base_url = _telemetry_base_url(cfg)
        if base_url:
            try:
                headers = {"X-DevHub-Secret": secret} if secret else {}
                r = requests.get(f"{base_url}/verify/status", params={"code": code}, headers=headers, timeout=5)
                if r.status_code == 200:
                    data = r.json()
                    if data.get("claimed"):
                        return data, None
            except Exception:
                pass  # naechster Versuch im naechsten Intervall

        time.sleep(POLL_INTERVAL_SECONDS)

    return None, "timeout"


def save_identity(cfg, save_config_fn, identity):
    cfg["discord_identity"] = {
        "discord_id": identity.get("discord_id"),
        "username": identity.get("username"),
        "display_name": identity.get("display_name"),
        "avatar_url": identity.get("avatar_url"),
        "roles": identity.get("roles", []),
        "linked_at": time.time(),
    }
    save_config_fn(cfg)
    return cfg["discord_identity"]


def clear_identity(cfg, save_config_fn):
    cfg["discord_identity"] = None
    save_config_fn(cfg)
