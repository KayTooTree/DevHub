"""
guild_store.py — Persistiert pro Discord-Server (Guild), welche Kanaele/
Rollen das automatische Setup angelegt hat (Welcome-Kanal, Log-Kanal,
Ticket-Kategorie, Moderator-Rolle, ...).

Einfaches JSON-File statt Datenbank -- reicht fuer die Groessenordnung
eines Coding-Studio-Servers voellig aus und kostet nichts.
"""

import json
import threading
from pathlib import Path

STORE_FILE = Path(__file__).resolve().parent / "guild_config.json"
_lock = threading.Lock()


def _load_all():
    if not STORE_FILE.exists():
        return {}
    try:
        with open(STORE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_all(data):
    with open(STORE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_guild(guild_id):
    with _lock:
        return _load_all().get(str(guild_id), {})


def set_guild(guild_id, **kwargs):
    with _lock:
        data = _load_all()
        entry = data.get(str(guild_id), {})
        entry.update(kwargs)
        data[str(guild_id)] = entry
        _save_all(data)
        return entry
