"""
verify_store.py — Kurzlebiger In-Memory-Speicher fuer Discord-Account-
Verknuepfungscodes.

Ablauf:
  1. DevHub Client generiert lokal einen zufaelligen Code, zeigt ihn an.
  2. Nutzer tippt /verify <code> in Discord -> register_claim() speichert
     die Discord-Identitaet (User-ID, Username, Anzeigename, Avatar,
     Rollen) unter diesem Code.
  3. Client pollt get_claim(code) ueber den Telemetrie-Server, bis
     "claimed" true ist, holt sich die Daten, verwirft den Code.

Bewusst NICHT persistiert (RAM reicht, Codes leben nur wenige Minuten) --
ein Neustart des Bots waehrend eine Verknuepfung laeuft ist ein
akzeptabler Rand-Fall (Nutzer generiert dann einfach einen neuen Code).
"""

import threading
import time

CODE_TTL_SECONDS = 300         # Code verfaellt nach 5 Minuten, wenn nicht eingeloest
CLAIMED_RETENTION_SECONDS = 120  # nach Einloesung noch 2 Minuten fuer den Client abholbar

_lock = threading.Lock()
_pending = {}  # code -> {"created_at", "claimed": bool, "claimed_at", identity-Felder...}


def register_pending(code):
    """Client-Seite ruft das nicht auf -- der Code existiert implizit,
    sobald jemand /verify damit ausfuehrt. Diese Funktion ist fuer den Bot,
    um doppelte Registrierung sauber zu handhaben."""
    with _lock:
        if code not in _pending:
            _pending[code] = {"created_at": time.time(), "claimed": False}


def register_claim(code, discord_id, username, display_name, avatar_url, roles):
    """Wird vom /verify-Command aufgerufen. Gibt False zurueck, wenn der
    Code bereits eingeloest wurde (Erst-Einloesung gewinnt)."""
    with _lock:
        _cleanup_locked()
        entry = _pending.get(code)
        if entry and entry.get("claimed"):
            return False  # schon vergeben
        _pending[code] = {
            "created_at": entry["created_at"] if entry else time.time(),
            "claimed": True,
            "claimed_at": time.time(),
            "discord_id": str(discord_id),
            "username": username,
            "display_name": display_name,
            "avatar_url": avatar_url,
            "roles": roles,
        }
        return True


def get_claim(code):
    with _lock:
        _cleanup_locked()
        return _pending.get(code)


def _cleanup_locked():
    now = time.time()
    expired = []
    for code, entry in _pending.items():
        if entry.get("claimed"):
            if now - entry.get("claimed_at", 0) > CLAIMED_RETENTION_SECONDS:
                expired.append(code)
        else:
            if now - entry.get("created_at", 0) > CODE_TTL_SECONDS:
                expired.append(code)
    for code in expired:
        del _pending[code]
