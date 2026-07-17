"""
audit_log.py — Einfaches Append-only-Protokoll aller Aktionen auf dem Agent.

Jede schreibende Aktion (Pull, Notiz senden) wird mit Zeitstempel, Operator-
Namen (vom Client mitgegeben) und Aktion protokolliert. Das Log ist absichtlich
nur lesbar ueber die API -- es gibt keinen Endpoint, um es zu loeschen oder
zu manipulieren.
"""

import json
import time
from pathlib import Path

MAX_ENTRIES_RETURNED = 200


def log_action(log_file: Path, username: str, action: str, detail: str = ""):
    entry = {
        "ts": time.time(),
        "username": username or "unbekannt",
        "action": action,
        "detail": detail,
    }
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass  # Logging darf die eigentliche Aktion nie blockieren
    return entry


def read_log(log_file: Path, limit=MAX_ENTRIES_RETURNED):
    if not log_file.exists():
        return []
    entries = []
    try:
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except Exception:
                    continue
    except Exception:
        return []
    return entries[-limit:][::-1]  # neueste zuerst
