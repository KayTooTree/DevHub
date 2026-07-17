"""
docker_tools.py — Liest den Status laufender Docker-Container aus, sofern
die Docker-CLI auf dem System verfuegbar ist. Kein hartes Abhaengigkeit:
ist Docker nicht installiert, liefert das Panel im Dashboard einfach einen
entsprechenden Hinweis statt eines Fehlers.
"""

import subprocess
import sys

IS_WINDOWS = sys.platform == "win32"


def docker_status():
    """Liste aller laufenden Container (docker ps). Bewusst nur laufende
    Container, nicht gestoppte -- das Dashboard soll auf einen Blick zeigen
    was gerade aktiv ist."""
    try:
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.ID}}|{{.Names}}|{{.Status}}|{{.Image}}|{{.Ports}}"],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if IS_WINDOWS else 0,
        )
        if result.returncode != 0:
            return {"available": False, "error": result.stderr.strip() or "Docker-Daemon nicht erreichbar"}

        containers = []
        for line in result.stdout.strip().splitlines():
            parts = line.split("|")
            if len(parts) == 5:
                containers.append({
                    "id": parts[0][:12],
                    "name": parts[1],
                    "status": parts[2],
                    "image": parts[3],
                    "ports": parts[4],
                })
        return {"available": True, "containers": containers}
    except FileNotFoundError:
        return {"available": False, "error": "Docker CLI nicht gefunden"}
    except subprocess.TimeoutExpired:
        return {"available": False, "error": "Zeitüberschreitung (Docker Desktop läuft?)"}
    except Exception as e:
        return {"available": False, "error": str(e)}
