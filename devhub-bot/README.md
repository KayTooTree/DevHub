# DEVHUB Bot

Discord-Bot fürs Coding-Studio: Moderation, Tickets, Logs, Willkommens-
nachrichten, automatisches Server-Setup — plus ein eingebauter Telemetrie-
Endpunkt, der Heartbeats/Feedback vom DevHub Client entgegennimmt und die
aktive Nutzerzahl als Bot-Presence anzeigt ("Watching X Users using DevHub").

## Was der Bot kann

**Moderation** (jeweils über Discords eigenes Berechtigungssystem
abgesichert, granular einstellbar unter Server-Einstellungen →
Integrationen):
- `/warn`, `/warnings`, `/clearwarnings`
- `/kick`, `/ban`, `/unban`
- `/timeout`, `/untimeout`

**Account-Verknüpfung** — `/verify CODE`: verknüpft einen DevHub-Client
mit der Discord-Identität des Nutzers (Anzeigename, Avatar, Rollen). Der
Code wird vorher im DevHub Client generiert und angezeigt. Codes sind
zufällig, 5 Minuten gültig und nur einmal einlösbar.

**Automatisches Server-Setup** — sobald der Bot einem (auch leeren) Server
beitritt, legt er automatisch an:
- Kategorie **DEVHUB STUDIO** mit `#welcome`, `#support`, `#mod-logs`
- Rolle **Moderator** (Kick/Ban/Timeout/Nachrichten verwalten)
- Kategorie **TICKETS** (privat, Ticket-Kanäle werden dynamisch erstellt)
- Ticket-Panel mit Button im `#support`-Kanal
- Kann jederzeit erneut angestoßen werden über `/setup` (idempotent —
  legt nur fehlende Teile neu an, nichts wird dupliziert)

**Tickets** — Klick auf den Button im Support-Kanal erstellt einen
privaten Kanal (sichtbar für Opener + Moderator-Rolle + Bot), mit
"Ticket schließen"-Button darin. Persistente Buttons — funktionieren auch
nach einem Bot-Neustart weiter.

**Logs** — Mod-Aktionen, gelöschte/bearbeitete Nachrichten, Server-Beitritt
landen automatisch in `#mod-logs`.

**Willkommensnachricht** — neue Mitglieder bekommen eine Begrüßung in
`#welcome`.

**Telemetrie** (`/info` zeigt die aktuelle Zahl) — nimmt anonyme
Heartbeats vom DevHub Client entgegen (siehe Architektur unten) und zeigt
"Watching X Users using DevHub" im **Bot-Profil** (nicht bei einzelnen
Nutzern sichtbar).

---

## 1. Bot bei Discord anlegen

1. [discord.com/developers/applications](https://discord.com/developers/applications)
   → "New Application"
2. Reiter **"Bot"** → "Reset Token" → Token kopieren (brauchst du gleich
   für `config.json`)
3. Auf derselben Seite unter **"Privileged Gateway Intents"** aktivieren:
   - ✅ **SERVER MEMBERS INTENT** (für Willkommensnachricht)
   - ✅ **MESSAGE CONTENT INTENT** (für Message-Logging)
4. Reiter **"OAuth2" → "URL Generator"**:
   - Scopes: `bot`, `applications.commands`
   - Bot-Permissions: mindestens `Manage Roles`, `Manage Channels`,
     `Kick Members`, `Ban Members`, `Moderate Members`, `Manage Messages`,
     `Send Messages`, `Embed Links`, `Read Message History` — am
     einfachsten: `Administrator` für den ersten Test, später granularer
   - Generierte URL öffnen → Bot auf deinen (Test-)Server einladen

## 2. Installation

```bash
cd devhub-bot
pip install -r requirements.txt
```

## 3. Konfiguration (`config.json`)

```json
{
  "bot_token": "DEIN_BOT_TOKEN",
  "telemetry_port": 8090,
  "shared_secret": "ein-zufaelliger-string",
  "feedback_channel_id": "KANAL_ID_FUER_FEEDBACK"
}
```

- `bot_token`: aus Schritt 1
- `shared_secret`: beliebiger zufälliger String — muss mit dem `secret`
  im DevHub Client übereinstimmen (siehe unten). Schützt den Heartbeat-/
  Feedback-Endpunkt vor zufälligem Spam. **Ehrlicher Hinweis**: Ein Secret
  im Client-Code ist kein Schutz gegen jemanden, der entschlossen den Code
  liest — reicht aber locker gegen zufälligen Missbrauch, was hier das
  eigentliche Ziel ist.
- `feedback_channel_id`: Rechtsklick auf den gewünschten Kanal → "ID
  kopieren" (Entwicklermodus muss in Discord aktiviert sein: Einstellungen
  → Erweitert → Entwicklermodus)

## 4. Starten

```bash
python3 bot.py
```

Oder `start_bot.bat` (Windows) / `start_bot.sh` (Linux/Mac).

### Als systemd-Service (empfohlen für Dauerbetrieb)

```bash
sudo useradd -r -s /usr/sbin/nologin devhub
sudo cp -r devhub-bot /opt/devhub-bot
sudo chown -R devhub:devhub /opt/devhub-bot
sudo cp devhub-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now devhub-bot
sudo journalctl -u devhub-bot -f
```

---

## Architektur: Heartbeat & Feedback (server_addr.txt)

Der DevHub Client soll die Adresse dieses Bots nicht hart im Code stehen
haben (falls du mal umziehst/den Port änderst). Stattdessen:

1. Du hostest eine kleine Textdatei `server_addr.txt` in einem öffentlichen
   GitHub-Repo mit genau einer Zeile Inhalt:
   ```
   http://DEINE-IP-ODER-DOMAIN:8090
   ```
2. Der DevHub Client liest diese Datei beim Start (und danach stündlich
   erneut) über die GitHub-Raw-URL, z.B.:
   ```
   https://raw.githubusercontent.com/KayTooTree/DevHub/main/server_addr.txt
   ```
3. Ziehst du den Bot auf einen anderen Server um, änderst du nur diese
   eine Datei im Repo — alle Clients holen sich automatisch die neue
   Adresse ab, ganz ohne Update des Clients selbst.

Im DevHub Client trägst du im Zahnrad-Menü unter **Feedback** ein, falls
`server_addr_url` von der Standard-URL abweicht, sowie das `shared_secret`
(muss mit dem hier in `config.json` übereinstimmen).

**Was genau gezählt wird**: Jede DevHub-Installation generiert einmalig
eine zufällige, rein lokale `instance_id` (keine Discord- oder sonstige
persönliche Identität). Alle 10 Sekunden schickt sie ein Lebenszeichen;
nach 30 Sekunden Funkstille gilt eine Instanz als "weg". Der Bot zählt nur
"wie viele Installationen sind gerade aktiv" — nicht wer.

---

## API-Referenz (intern, für den DevHub Client)

Alle Endpunkte optional per `X-DevHub-Secret`-Header geschützt (siehe
`shared_secret` in `config.json`).

| Methode | Pfad | Zweck |
|---|---|---|
| GET | `/health` | Health-Check + aktuelle aktive Instanzen, kein Secret nötig |
| POST | `/heartbeat` | `{"instance_id": "..."}` — Lebenszeichen |
| POST | `/feedback` | `{"instance_id": "...", "text": "..."}` — postet in `feedback_channel_id` |
| GET | `/verify/status?code=X` | Prüft, ob ein DevHub-Verify-Code eingelöst wurde |

---

## Troubleshooting

- **Bot kommt online, aber `/setup` schlägt fehl** → Bot-Rolle braucht
  "Rollen verwalten" + "Kanäle verwalten", und muss in der Rollenliste
  über allen Rollen stehen, die er verwalten soll.
- **Willkommensnachricht kommt nicht an** → SERVER MEMBERS INTENT im
  Developer Portal aktiviert? (Schritt 1.3)
- **Message-Logging (Edit/Delete) leer** → MESSAGE CONTENT INTENT aktiviert?
- **Ticket-Buttons reagieren nach Neustart nicht mehr** → sollte eigentlich
  nicht passieren (persistente Views), prüf die Bot-Logs auf Fehler beim
  Start von `cogs.tickets`.
- **Heartbeat kommt nicht an** → `shared_secret` in Client und Bot
  identisch? `server_addr.txt` korrekt erreichbar (`curl` die Raw-URL testen)?
