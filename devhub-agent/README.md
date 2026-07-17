# DEVHUB Agent

Der Agent läuft **auf einem Server** (VPS, Root-Server, Home-Server, ...) und
macht diesen Server im DEVHUB Client auf deinem eigenen PC sichtbar: Systemstatus,
Git-Repo-Übersicht mit Pull-Button, geteilte Notizen und ein Audit-Log.

## Sicherheitsprinzip (wichtig zu verstehen)

- **Kein Remote-Terminal, keine beliebigen Befehle.** Der Agent hat keine
  "führe Befehl X aus"-Route. Die einzige Aktion mit Seiteneffekt ist
  `git pull` — und zwar ausschließlich für Pfade, die du vorher explizit in
  `repos.json` **auf diesem Server** eingetragen hast (Whitelist). Ein
  Angreifer, der den API-Key errät, kann damit maximal deine konfigurierten
  Repos pullen — nicht mehr.
- **Jede Route außer `/health` verlangt einen API-Key** im Header
  `Authorization: Bearer <key>`. Der Key wird beim allerersten Start
  automatisch generiert (siehe Konsolen-Ausgabe) und dauerhaft in
  `agent_config.json` gespeichert.
- **Brute-Force-Schutz**: Nach mehreren Fehlversuchen von derselben IP wird
  diese IP temporär gesperrt (Standard: 8 Versuche / 60s Fenster / 5 Minuten Sperre).
- **Der Agent bindet auf `0.0.0.0`** (überall im Netzwerk erreichbar), damit
  dein Client ihn von deinem PC aus erreichen kann. Das heißt aber auch:
  jeder im gleichen Netzwerk kann Anfragen schicken (auch wenn ungültige
  Keys immer abgelehnt werden). **Setz den Port NICHT direkt frei ins offene
  Internet.** Nutze stattdessen:
  - Ein VPN zwischen deinem PC und dem Server (Tailscale, WireGuard) — die
    sauberste Lösung
  - Eine Firewall-Regel, die den Port nur für deine eigene IP freigibt
  - SSH-Port-Forwarding (`ssh -L 8060:localhost:8060 user@server`)

## Installation

Voraussetzung: Python 3.9+ und Git im PATH auf dem Server.

```bash
cd devhub-agent
pip install -r requirements.txt
```

## Konfiguration

1. `repos.json` bearbeiten — trag genau die Repo-Pfade ein, die der Agent
   pullen darf:

```json
[
  { "name": "Mein Projekt", "path": "/home/kay/projekte/mein-projekt" }
]
```

2. `agent_config.json` bearbeiten (Servername, Port):

```json
{
  "name": "VPS Frankfurt",
  "api_key": "",
  "host": "0.0.0.0",
  "port": 8060
}
```

`api_key` leer lassen — wird beim ersten Start automatisch generiert und
in der Konsole ausgegeben. **Diesen Key brauchst du gleich im DEVHUB
Client**, um den Server zu verlinken.

## Starten

```bash
python3 agent.py
```

Der generierte API-Key erscheint einmalig in der Konsole und steht danach
dauerhaft in `agent_config.json`.

### Als systemd-Service (empfohlen für Dauerbetrieb)

```bash
sudo useradd -r -s /usr/sbin/nologin devhub   # eigener, unprivilegierter Nutzer
sudo cp -r devhub-agent /opt/devhub-agent
sudo chown -R devhub:devhub /opt/devhub-agent
sudo cp devhub-agent.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now devhub-agent
sudo journalctl -u devhub-agent -f   # Logs ansehen (u.a. der generierte API-Key beim ersten Start)
```

### Unter Windows (z.B. Windows-Server)

`start_agent.bat` doppelklicken, oder über den Taskplaner beim Systemstart
ausführen lassen (Aktion: `python.exe agent.py`, "Starte in" auf den
Agent-Ordner setzen).

## Im DEVHUB Client verlinken

Im Client-Dashboard unter "REMOTE SERVERS" → "Server hinzufügen":

- **Name**: frei wählbar (erscheint als Kartentitel)
- **Host**: IP oder Hostname des Servers (z.B. `10.0.0.5` oder über VPN `100.x.x.x`)
- **Port**: der in `agent_config.json` konfigurierte Port (Standard `8060`)
- **API-Key**: der beim ersten Agent-Start generierte Key

Der Key wird ausschließlich im lokalen Backend deines Clients gespeichert
(nie im Browser sichtbar).

## Server-Monitor-Panel (der "Küchenmonitor")

Neben der reinen API hat der Agent auch eine eigene kleine Weboberfläche,
direkt auf dem Server aufrufbar:

```
http://<server-ip>:8060/panel
```

Zeigt live:
- **Notizen/Changelogs**, die von einem DEVHUB Client geschickt wurden —
  neue Einträge poppen sofort auf (Prinzip wie eine Küchenmonitor-Anzeige:
  Kasse sendet, Monitor zeigt an)
- **Aktivitäts-Log**: wer hat wann gepullt oder eine Notiz geschickt
- Kompakter Status: Hostname, CPU/RAM, Uptime, Repo-Status

Praktisch, wenn du diesen Server sowieso per RDP/Konsole offen hast, oder
einen Monitor/Screen direkt am Server angeschlossen hast (Server-Raum,
Home-Lab, etc.) — du siehst Notizen deines Teams live, ohne extra
nachzuschauen.

**Zugriff**: Du brauchst denselben API-Key wie sonst auch. Entweder einmalig
im Panel eingeben (mit "auf diesem Gerät merken" wird er lokal im Browser
gespeichert), oder direkt als Link mit `#token=DEIN_KEY` aufrufen — dann
fragt es nicht erneut. Der Key steht dabei nur im URL-Fragment (`#...`),
das wird nie an den Server mitgeschickt und taucht nicht in Server-Logs auf.

Für einen dauerhaften "Monitor-Modus" (z.B. auf einem Bildschirm im
Serverraum): Browser im Kiosk-Modus starten und die URL mit `#token=...`
als Startseite setzen.

## API-Referenz (für den Fall, dass du selbst etwas bauen willst)

Alle Routen außer `/health` brauchen `Authorization: Bearer <api_key>`.

| Methode | Pfad | Zweck |
|---|---|---|
| GET | `/health` | Erreichbarkeits-Check, kein Auth |
| GET | `/panel` | Server-Monitor-Weboberfläche (HTML, kein Auth zum Laden — Daten dahinter brauchen den Key) |
| GET | `/status` | Hostname, OS, CPU/RAM/Disk |
| GET | `/processes` | Top-Prozesse nach CPU |
| GET | `/ports` | Lauschende Ports |
| GET | `/docker` | Laufende Docker-Container (falls vorhanden) |
| GET | `/repos` | Git-Status aller Repos aus `repos.json` |
| POST | `/repos/pull` | `{"path": "...", "username": "..."}` — Pull für ein Repo |
| POST | `/repos/pull_all` | `{"username": "..."}` — Pull für alle Repos |
| GET | `/notes` | Liste geteilter Notizen `[{author, text, ts}]` |
| POST | `/notes` | `{"text": "...", "username": "..."}` — Notiz hinzufügen |
| GET | `/logs` | Audit-Log (neueste zuerst) |

## Troubleshooting

- **"unauthorized"** → API-Key falsch/fehlt, oder falsche Schreibweise im
  `Authorization`-Header (muss exakt `Bearer <key>` sein).
- **"Zu viele Fehlversuche"** → Brute-Force-Sperre aktiv, ein paar Minuten
  warten oder `agent_config.json`-Werte für `rate_limit_*` anpassen.
- **Repo zeigt "MISSING"** → Pfad in `repos.json` existiert auf diesem
  Server nicht oder ist falsch geschrieben.
- **Pull schlägt fehl mit "nicht whitelisted"** → Der übergebene Pfad steht
  nicht exakt (Zeichen für Zeichen) in `repos.json`.
