# DEVHUB v2 — Cyber Command Center

Dein persönliches Developer-Dashboard im edex-ui-Stil. Läuft komplett lokal
auf deinem PC.

## Features

- **Voll eingebettetes Live-Terminal** — echte PowerShell/Bash direkt im
  Browser (xterm.js über WebSocket an eine echte PTY gebunden, wie bei
  edex-ui / Wetty / ttyd). Kein Simulations-Terminal, du tippst wirklich in
  eine echte Shell.
- **DE/EN Sprachumschaltung** — Button oben rechts, Einstellung wird in
  `config.json` gespeichert und bleibt über Neustarts erhalten.
- **Uhrzeit / Datum**
- **CPU / RAM / Disk-Auslastung**
- **Lokale IP + öffentliche IP + Geolocation** (Stadt, ISP, Timezone, Koordinaten)
- **Erweiterter Git-Repo-Status**: Branch, Ahead/Behind, uncommitted changes,
  Pull-Button, "Öffne in VS Code"-Button, "Öffne im Explorer"-Button
- **Top-Prozesse** nach CPU-Last
- **Offene Ports** — sofort sehen, welche Dev-Server (Vite, Flask, Node, ...)
  gerade laufen
- **Schnellnotizen** mit Autosave (persistiert in `notes.txt`)
- **Quick-Launch-Buttons** — frei konfigurierbar in `config.json`
  (VS Code, Explorer, Windows Terminal, Docker Desktop, ...)

---

## 1. Installation

Voraussetzung: Python 3.9+ und Git im PATH.

```powershell
cd devhub
pip install -r requirements.txt
```

`pywinpty` (für das eingebettete Terminal auf Windows) wird automatisch mit
installiert — Windows bekommt darüber ein `ConPTY`-Handle für eine echte
interaktive Shell.

## 2. Repos konfigurieren

`repos.json` mit deinen echten lokalen Repo-Pfaden füllen:

```json
[
  { "name": "NPStarter", "path": "C:\\Users\\Kay\\Projects\\NPStarter" }
]
```

## 3. config.json anpassen

```json
{
  "language": "de",
  "shell_windows": "powershell.exe",
  "shell_unix": "bash",
  "quick_launch": [
    { "label": "VS Code", "command": "code ." },
    { "label": "Docker Desktop", "command": "\"C:\\Program Files\\Docker\\Docker\\Docker Desktop.exe\"" }
  ]
}
```

- `language`: `"de"` oder `"en"` (kann auch im Dashboard per Klick geändert
  werden — wird automatisch zurückgeschrieben)
- `shell_windows` / `shell_unix`: welche Shell das eingebettete Terminal
  startet (z. B. `"pwsh.exe"` für PowerShell 7, `"cmd.exe"`, `"zsh"`, ...)
- `quick_launch`: beliebige Buttons mit Shell-Befehlen, die per Klick
  ausgeführt werden

## 4. Manuell testen

```powershell
python server.py
```

Dann im Browser: `http://127.0.0.1:5050`

Oder `start.bat` doppelklicken (zeigt Konsole zum Debuggen).

## 5. In den Autostart packen

1. `Win + R` → `shell:startup` → Enter
2. `start_hidden.vbs` in diesen Ordner legen (oder eine Verknüpfung dorthin)
3. Fertig — beim nächsten Login startet der Server unsichtbar im Hintergrund
   und der Browser öffnet automatisch das Dashboard

## 6. Server stoppen

```powershell
Get-Process pythonw | Stop-Process
```

---

## Architektur

```
devhub/
  server.py           Flask + Flask-SocketIO Hauptserver
  config.json          Sprache, Shell-Wahl, Quick-Launch-Buttons
  repos.json           Liste der überwachten Git-Repos
  notes.txt             (wird automatisch erstellt) Schnellnotizen
  helpers/
    system_info.py      CPU/RAM/Disk, IP/Geo, Top-Prozesse, offene Ports
    git_tools.py         Git-Status, Pull, "Öffne in Tool"
    pty_bridge.py        Terminal-Sessions (PTY <-> WebSocket)
  static/
    index.html           HUD-Layout
    style.css             Cyber/Military-Theme
    i18n.js                DE/EN-Übersetzungen
    terminal.js            xterm.js + Socket.IO-Anbindung
    app.js                  Restliche Dashboard-Logik
```

**Warum ein Backend?** Eine reine HTML-Seite darf aus Sicherheitsgründen
weder deine Festplatte nach Git-Repos durchsuchen, noch eine echte Shell
starten. Deshalb läuft im Hintergrund ein kleiner Python-Server, der nur
auf `127.0.0.1` lauscht — von außen nicht erreichbar.

**Wie das eingebettete Terminal funktioniert:** Der Browser öffnet eine
WebSocket-Verbindung (Socket.IO) zum Server. Für jede Verbindung startet
der Server eine echte Shell (PowerShell/Bash), gebunden an ein
Pseudo-Terminal (PTY). Tastatureingaben aus xterm.js gehen 1:1 an die
Shell, deren Output kommt live zurück. Genau dieses Prinzip nutzen auch
edex-ui, Wetty und ttyd.

---

## Troubleshooting

- **"BACKEND LINK: LOST"** → Server läuft nicht. `start.bat` ausführen und
  Fehlermeldung lesen.
- **Terminal-Panel bleibt leer / verbindet nicht** → Firewall/Antivirus
  könnte lokale WebSocket-Verbindungen blockieren; prüfe die Server-Konsole
  auf Fehler beim Start der Shell (z. B. falscher Pfad in `shell_windows`).
- **`pip install pywinpty` schlägt fehl** → meist fehlende Build Tools;
  meist reicht `pip install --upgrade pip` vorher, da für gängige
  Python-Versionen fertige Wheels existieren.
- **Repo zeigt "NO_UPSTREAM"** → `git branch --set-upstream-to=origin/main`
  im jeweiligen Repo ausführen.
- **Öffentliche IP zeigt "OFFLINE"** → keine Internetverbindung oder
  ip-api.com nicht erreichbar.
- **Quick-Launch-Button tut nichts** → Pfad/Befehl in `config.json` prüfen,
  bei Pfaden mit Leerzeichen in Anführungszeichen setzen (siehe Docker-Beispiel).
