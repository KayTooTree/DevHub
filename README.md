# DEVHUB v3 — Cyber Command Center

Dein persönliches Developer-Dashboard im edex-ui-Stil. Läuft komplett lokal
auf deinem PC.

## Was ist neu in v3

- **Terminal-Eingabe-Bug gefixt**: Der Grund, warum du nicht ins Terminal
  tippen konntest — der Container hatte kein `position: relative`, was
  xterm.js zwingend braucht, um sein unsichtbares Eingabefeld richtig zu
  positionieren. Behoben.
- **Terminal-Tabs**: beliebig viele parallele Shell-Sessions, jede mit
  eigener echter PowerShell/Bash-Instanz. Tabs laufen im Hintergrund weiter,
  auch wenn du zu einem anderen wechselst.
- **Boot-Animation**: kurzer "Systemhochfahren"-Screen beim Laden, mit
  Skip-Button falls es dir zu langsam ist.
- **Operator = echter PC-Benutzername**, automatisch per `getpass.getuser()`
  ermittelt (nicht mehr hartcodiert).
- **Ping-Latenz-Anzeige** im Status-Strip (Internetverbindung auf einen Blick).
- **Akkustatus** (falls Laptop) im Status-Strip.
- **Docker-Container-Panel** — sofern Docker installiert ist, siehst du alle
  laufenden Container mit Status und Image.
- **GitHub-Sterne/Issues-Badge** in der Repo-Tabelle (optional, ganz ohne
  Token — nutzt die öffentliche GitHub-API mit 5-Minuten-Cache).

## Alle Features im Überblick

- Voll eingebettetes Live-Terminal mit Tabs (echte Shell über WebSocket/PTY)
- DE/EN Sprachumschaltung (Button oben rechts, persistiert in `config.json`)
- Uhrzeit / Datum
- CPU / RAM / Disk-Auslastung
- Lokale IP + öffentliche IP + Geolocation
- Ping-Latenz + Akkustatus
- Erweiterter Git-Repo-Status: Branch, Ahead/Behind, uncommitted changes,
  GitHub-Sterne/Issues, Pull-Button, "Öffne in VS Code", "Öffne im Explorer"
- Top-Prozesse nach CPU-Last
- Offene Ports
- Docker-Container-Übersicht
- Schnellnotizen mit Autosave
- Frei konfigurierbare Quick-Launch-Buttons
- Boot-Animation beim Start

---

## 1. Installation

Voraussetzung: Python 3.9+ und Git im PATH.

```powershell
cd devhub
pip install -r requirements.txt
```

`pywinpty` (fürs eingebettete Terminal auf Windows) wird automatisch
mitinstalliert.

## 2. Repos konfigurieren (`repos.json`)

```json
[
  {
    "name": "NPStarter",
    "path": "C:\\Users\\Kay\\Projects\\NPStarter",
    "github": "DeinGithubUser/NPStarter"
  }
]
```

Das Feld `"github"` ist **optional** — nur setzen, wenn du Sterne/Issues in
der Tabelle sehen willst. Ohne Internetzugriff oder bei privaten Repos
zeigt das Badge einfach nichts an, kein Fehler.

## 3. `config.json` anpassen

```json
{
  "language": "de",
  "shell_windows": "powershell.exe",
  "shell_unix": "bash",
  "ping_host": "8.8.8.8",
  "quick_launch": [
    { "label": "VS Code", "command": "code ." },
    { "label": "Docker Desktop", "command": "\"C:\\Program Files\\Docker\\Docker\\Docker Desktop.exe\"" }
  ]
}
```

- `language`: `"de"` / `"en"` — auch per Klick im Dashboard änderbar
- `shell_windows` / `shell_unix`: welche Shell jeder neue Terminal-Tab startet
- `ping_host`: welcher Host für die Latenzmessung angepingt wird
- `quick_launch`: beliebige Buttons mit Shell-Befehlen

## 4. Manuell testen

```powershell
python server.py
```

Dann im Browser: `http://127.0.0.1:5050`

Oder `start.bat` doppelklicken (zeigt Konsole zum Debuggen).

## 5. In den Autostart packen

1. `Win + R` → `shell:startup` → Enter
2. `start_hidden.vbs` (oder eine Verknüpfung dazu) in diesen Ordner legen
3. Fertig

## 6. Server stoppen

```powershell
Get-Process pythonw | Stop-Process
```

---

## Architektur

```
devhub/
  server.py             Flask + Flask-SocketIO Hauptserver
  config.json            Sprache, Shell-Wahl, Ping-Host, Quick-Launch
  repos.json              überwachte Git-Repos (+ optionale GitHub-Slugs)
  notes.txt                (wird automatisch erstellt) Schnellnotizen
  helpers/
    system_info.py         CPU/RAM/Disk, IP/Geo, Username, Battery, Ping, Top-Prozesse, Ports
    git_tools.py            Git-Status, Pull, "Öffne in Tool"
    docker_tools.py         Docker-Container-Status
    github_tools.py         Öffentliche GitHub-Repo-Statistiken (mit Cache)
    pty_bridge.py           Terminal-Sessions (PTY <-> WebSocket)
  static/
    index.html              HUD-Layout inkl. Boot-Screen & Terminal-Tabs
    style.css                Cyber/Military-Theme
    i18n.js                   DE/EN-Übersetzungen
    boot.js                    Start-Animation
    terminal.js                xterm.js + Tabs + Socket.IO-Anbindung
    app.js                      Restliche Dashboard-Logik
```

**Warum ein Backend?** Eine reine HTML-Seite darf aus Sicherheitsgründen
weder deine Festplatte nach Git-Repos durchsuchen noch eine echte Shell
starten. Der Server lauscht ausschließlich auf `127.0.0.1` — von außen
nicht erreichbar.

**Wie das Terminal funktioniert:** Jeder Tab öffnet eine eigene
Socket.IO-Verbindung. Für jede Verbindung startet der Server eine echte
Shell (PowerShell/Bash) an ein Pseudo-Terminal (PTY) gebunden. Tastatur-
eingaben aus xterm.js gehen 1:1 an die Shell, deren Output kommt live
zurück — genau das Prinzip von edex-ui, Wetty und ttyd.

---

## Troubleshooting

- **Ins Terminal tippen geht immer noch nicht** → Browser-Cache leeren
  (Strg+Shift+R), da `style.css` sich geändert hat. Prüfe in den
  Browser-Devtools (F12 → Console), ob Fehler beim Laden von xterm.js oder
  Socket.IO auftauchen (z. B. wegen geblockter CDN-Domains).
- **"BACKEND LINK: LOST"** → Server läuft nicht. `start.bat` ausführen und
  Fehlermeldung lesen.
- **Docker-Panel zeigt "nicht verfügbar"** → Docker Desktop läuft nicht oder
  ist nicht installiert; kein Fehler, einfach ignorieren falls nicht genutzt.
- **GitHub-Badge fehlt** → Repo ist privat, falscher Slug, oder das
  öffentliche Rate-Limit (60 Anfragen/Stunde) ist erreicht — probier's in
  ein paar Minuten erneut.
- **Ping zeigt immer "--"** → ICMP evtl. von deiner Firewall geblockt, oder
  `ping_host` in `config.json` nicht erreichbar.
- **Repo zeigt "NO_UPSTREAM"** → `git branch --set-upstream-to=origin/main`
  im jeweiligen Repo ausführen.
- **Quick-Launch-Button tut nichts** → Pfad/Befehl in `config.json` prüfen,
  bei Leerzeichen im Pfad Anführungszeichen setzen (siehe Docker-Beispiel).
