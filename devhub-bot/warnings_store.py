"""
warnings_store.py — Persistente Verwarnungen pro (Guild, User).

Struktur: { "<guild_id>": { "<user_id>": [ {moderator_id, reason, ts}, ... ] } }
"""

import json
import threading
import time
from pathlib import Path

STORE_FILE = Path(__file__).resolve().parent / "warnings_store.json"
_lock = threading.Lock()


def _load():
    if not STORE_FILE.exists():
        return {}
    try:
        with open(STORE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save(data):
    with open(STORE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def add_warning(guild_id, user_id, moderator_id, reason):
    with _lock:
        data = _load()
        guild_key, user_key = str(guild_id), str(user_id)
        data.setdefault(guild_key, {}).setdefault(user_key, [])
        entry = {"moderator_id": str(moderator_id), "reason": reason, "ts": time.time()}
        data[guild_key][user_key].append(entry)
        _save(data)
        return len(data[guild_key][user_key])


def get_warnings(guild_id, user_id):
    with _lock:
        data = _load()
        return data.get(str(guild_id), {}).get(str(user_id), [])


def clear_warnings(guild_id, user_id):
    with _lock:
        data = _load()
        guild_key, user_key = str(guild_id), str(user_id)
        count = len(data.get(guild_key, {}).get(user_key, []))
        if guild_key in data and user_key in data[guild_key]:
            del data[guild_key][user_key]
            _save(data)
        return count
