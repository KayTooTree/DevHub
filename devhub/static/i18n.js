/*
 * i18n.js — Sprachverwaltung fuer DEVHUB (Deutsch/Englisch).
 *
 * Alle Textbausteine liegen zentral in I18N. Elemente im HTML markieren
 * ihren uebersetzbaren Text ueber data-i18n="key" (fuer textContent) bzw.
 * data-i18n-placeholder="key" (fuer Input/Textarea-Platzhalter).
 *
 * Die aktuelle Sprache wird server-seitig in config.json persistiert,
 * damit sie nach einem Neustart erhalten bleibt (kein localStorage noetig).
 */

const I18N = {
  de: {
    subtitle: "// CYBER COMMAND CENTER",
    link_active: "VERBINDUNG AKTIV",
    operator: "OPERATOR",
    node: "KNOTEN",
    sys_uptime: "LAUFZEIT",
    panel_system: "SYSTEMSTATUS",
    cpu_load: "CPU LAST",
    memory: "SPEICHER",
    disk: "FESTPLATTE",
    panel_network: "NETZWERK / IP TRACE",
    local_ip: "LOKALE IP",
    public_ip: "ÖFFENTLICHE IP",
    isp: "PROVIDER",
    location: "STANDORT",
    timezone: "ZEITZONE",
    coords: "KOORDINATEN",
    offline: "OFFLINE",
    panel_terminal: "LIVE TERMINAL",
    open_external: "EXTERNES FENSTER",
    panel_repos: "GIT REPOSITORY SYNC",
    pull_all: "ALLE PULLEN",
    th_repo: "REPO",
    th_branch: "BRANCH",
    th_status: "STATUS",
    th_detail: "DETAIL",
    th_actions: "AKTIONEN",
    pull: "PULL",
    code_btn: "CODE",
    explorer_btn: "ORDNER",
    panel_processes: "TOP PROZESSE",
    th_process: "PROZESS",
    th_cpu: "CPU%",
    th_mem: "MEM%",
    panel_ports: "OFFENE PORTS",
    th_port: "PORT",
    th_pid: "PID",
    panel_notes: "SCHNELLNOTIZEN",
    notes_placeholder: "Notizen hier eintippen — speichert automatisch...",
    saved: "GESPEICHERT",
    panel_launcher: "SCHNELLSTART",
    footer_ok: "BACKEND VERBINDUNG: OK",
    footer_lost: "BACKEND VERBINDUNG: VERLOREN",
    scanning: "DURCHSUCHE REPOSITORIES...",
    no_repos: "Keine Repos konfiguriert — repos.json bearbeiten",
    no_processes: "psutil nicht installiert",
    no_ports: "Keine offenen Ports gefunden",
    dirty_suffix: "ungespeicherte Änderung(en)",
    behind_suffix: "Commit(s) hinter Remote",
    ahead_suffix: "Commit(s) voraus",
    diverged_label: "vor",
    up_to_date: "Alles aktuell",
    ping: "PING",
    panel_docker: "DOCKER CONTAINER",
    th_container: "CONTAINER",
    th_image: "IMAGE",
    docker_unavailable: "Docker nicht verfügbar",
    no_containers: "Keine laufenden Container",
    panel_servers: "REMOTE SERVERS",
    add_server: "SERVER HINZUFÜGEN",
    loading_servers: "Lade Server...",
    no_servers: "Noch keine Server verlinkt",
    server_online: "ONLINE",
    server_offline: "OFFLINE",
    open_panel: "PANEL ÖFFNEN",
    remove_server: "Entfernen",
    confirm_remove_server: "Diesen Server wirklich entfernen? (Der Agent selbst läuft weiter.)",
    modal_add_server_title: "Server hinzufügen",
    field_name: "Name",
    field_host: "Host / IP",
    field_port: "Port",
    field_token: "API-Key",
    save: "SPEICHERN",
    cancel: "ABBRECHEN",
    tab_performance: "LEISTUNG",
    tab_repos: "REPOS",
    tab_notes: "NOTIZEN",
    tab_logs: "LOGS",
    send_note: "SENDEN",
    note_placeholder: "Changelog / Notiz an den Server schreiben...",
    no_notes: "Noch keine Notizen",
    no_logs: "Noch keine Log-Einträge",
    server_uptime_label: "UPTIME",
    server_hostname_label: "HOSTNAME",
    server_os_label: "OS",
    all_fields_required: "Alle Felder sind erforderlich",
    connection_failed: "Verbindung fehlgeschlagen",
    settings_title: "EINSTELLUNGEN",
    welcome_title: "WILLKOMMEN BEI DEVHUB",
    welcome_hint: "Kurz einrichten, bevor's losgeht — dauert eine Minute. Alles lässt sich später über das Zahnrad-Symbol oben rechts wieder ändern.",
    tab_profile: "PROFIL",
    field_display_name: "Anzeigename",
    field_display_name_placeholder: "z.B. Kay",
    display_name_hint: "Erscheint im Audit-Log verlinkter Server, wenn du remote pullst oder Notizen sendest.",
    display_name_required: "Bitte einen Anzeigenamen eingeben.",
    skip_for_now: "SPÄTER",
    finish_setup: "FERTIG",
    settings_load_error: "Konnte nicht geladen werden.",
    no_repos_yet: "Noch keine Repos eingetragen.",
    field_repo_name: "Name",
    field_repo_name_placeholder: "z.B. NPStarter",
    field_repo_path: "Lokaler Pfad",
    field_repo_path_placeholder: "C:\\Users\\...\\Projekte\\NPStarter",
    field_repo_github: "GitHub-Slug (optional)",
    field_repo_github_placeholder: "dein-user/repo-name",
    add_repo: "REPO HINZUFÜGEN",
    repo_name_path_required: "Name und Pfad sind erforderlich.",
    tab_discord: "DISCORD",
    discord_hint: "Der \"View DevHub\"-Link-Button im Discord-Profil ist fest eingebaut und zeigt immer auf das DevHub-Repo. Alles andere hier ist frei einstellbar.",
    field_discord_enabled: "Discord Rich Presence aktivieren",
    field_discord_client_id: "Discord Application ID",
    field_discord_client_id_placeholder: "von discord.com/developers/applications",
    field_discord_details: "Erste Zeile (Details)",
    field_discord_live_status: "Live-Status als zweite Zeile anzeigen (z.B. \"2 repos behind\")",
    field_discord_state: "Zweite Zeile (statisch, nur falls Live-Status aus)",
    field_discord_state_placeholder: "optional",
    field_discord_image_key: "Bild-Asset-Key (optional)",
    field_discord_image_key_placeholder: "aus Discord Developer Portal -> Rich Presence -> Art Assets",
    field_discord_image_text: "Bild-Tooltip-Text (optional)",
    discord_button_hint: "Der Link-Button lässt sich hier nicht ändern — er ist absichtlich fest auf das DevHub-Repo verankert.",
  },
  en: {
    subtitle: "// CYBER COMMAND CENTER",
    link_active: "LINK ACTIVE",
    operator: "OPERATOR",
    node: "NODE",
    sys_uptime: "UPTIME",
    panel_system: "SYSTEM STATUS",
    cpu_load: "CPU LOAD",
    memory: "MEMORY",
    disk: "DISK",
    panel_network: "NETWORK / IP TRACE",
    local_ip: "LOCAL IP",
    public_ip: "PUBLIC IP",
    isp: "ISP",
    location: "LOCATION",
    timezone: "TIMEZONE",
    coords: "COORDS",
    offline: "OFFLINE",
    panel_terminal: "LIVE TERMINAL",
    open_external: "EXTERNAL WINDOW",
    panel_repos: "GIT REPOSITORY SYNC",
    pull_all: "PULL ALL",
    th_repo: "REPO",
    th_branch: "BRANCH",
    th_status: "STATUS",
    th_detail: "DETAIL",
    th_actions: "ACTIONS",
    pull: "PULL",
    code_btn: "CODE",
    explorer_btn: "FOLDER",
    panel_processes: "TOP PROCESSES",
    th_process: "PROCESS",
    th_cpu: "CPU%",
    th_mem: "MEM%",
    panel_ports: "OPEN PORTS",
    th_port: "PORT",
    th_pid: "PID",
    panel_notes: "QUICK NOTES",
    notes_placeholder: "Type notes here — autosaves...",
    saved: "SAVED",
    panel_launcher: "QUICK LAUNCH",
    footer_ok: "BACKEND LINK: OK",
    footer_lost: "BACKEND LINK: LOST",
    scanning: "SCANNING REPOSITORIES...",
    no_repos: "No repos configured — edit repos.json",
    no_processes: "psutil not installed",
    no_ports: "No open ports found",
    dirty_suffix: "uncommitted change(s)",
    behind_suffix: "commit(s) behind remote",
    ahead_suffix: "commit(s) ahead",
    diverged_label: "ahead",
    up_to_date: "Everything up to date",
    ping: "PING",
    panel_docker: "DOCKER CONTAINERS",
    th_container: "CONTAINER",
    th_image: "IMAGE",
    docker_unavailable: "Docker not available",
    no_containers: "No running containers",
    panel_servers: "REMOTE SERVERS",
    add_server: "ADD SERVER",
    loading_servers: "Loading servers...",
    no_servers: "No servers linked yet",
    server_online: "ONLINE",
    server_offline: "OFFLINE",
    open_panel: "OPEN PANEL",
    remove_server: "Remove",
    confirm_remove_server: "Really remove this server? (The agent itself keeps running.)",
    modal_add_server_title: "Add Server",
    field_name: "Name",
    field_host: "Host / IP",
    field_port: "Port",
    field_token: "API Key",
    save: "SAVE",
    cancel: "CANCEL",
    tab_performance: "PERFORMANCE",
    tab_repos: "REPOS",
    tab_notes: "NOTES",
    tab_logs: "LOGS",
    send_note: "SEND",
    note_placeholder: "Write a changelog / note to the server...",
    no_notes: "No notes yet",
    no_logs: "No log entries yet",
    server_uptime_label: "UPTIME",
    server_hostname_label: "HOSTNAME",
    server_os_label: "OS",
    all_fields_required: "All fields are required",
    connection_failed: "Connection failed",
    settings_title: "SETTINGS",
    welcome_title: "WELCOME TO DEVHUB",
    welcome_hint: "Quick setup before we start — takes a minute. Everything can be changed later via the gear icon top right.",
    tab_profile: "PROFILE",
    field_display_name: "Display name",
    field_display_name_placeholder: "e.g. Kay",
    display_name_hint: "Shows up in the audit log of linked servers when you pull remotely or send notes.",
    display_name_required: "Please enter a display name.",
    skip_for_now: "LATER",
    finish_setup: "DONE",
    settings_load_error: "Could not load.",
    no_repos_yet: "No repos configured yet.",
    field_repo_name: "Name",
    field_repo_name_placeholder: "e.g. NPStarter",
    field_repo_path: "Local path",
    field_repo_path_placeholder: "C:\\Users\\...\\Projects\\NPStarter",
    field_repo_github: "GitHub slug (optional)",
    field_repo_github_placeholder: "your-user/repo-name",
    add_repo: "ADD REPO",
    repo_name_path_required: "Name and path are required.",
    tab_discord: "DISCORD",
    discord_hint: "The \"View DevHub\" link button in your Discord profile is fixed and always points to the DevHub repo. Everything else here is freely configurable.",
    field_discord_enabled: "Enable Discord Rich Presence",
    field_discord_client_id: "Discord Application ID",
    field_discord_client_id_placeholder: "from discord.com/developers/applications",
    field_discord_details: "First line (details)",
    field_discord_live_status: "Show live status as second line (e.g. \"2 repos behind\")",
    field_discord_state: "Second line (static, only if live status is off)",
    field_discord_state_placeholder: "optional",
    field_discord_image_key: "Image asset key (optional)",
    field_discord_image_key_placeholder: "from Discord Developer Portal -> Rich Presence -> Art Assets",
    field_discord_image_text: "Image tooltip text (optional)",
    discord_button_hint: "The link button can't be changed here — it's intentionally fixed to the DevHub repo.",
  },
};

let currentLang = "de";
let _i18nResolveReady;
window.i18nReadyPromise = new Promise((resolve) => { _i18nResolveReady = resolve; });

function t(key) {
  return (I18N[currentLang] && I18N[currentLang][key]) || key;
}

function localeTag() {
  return currentLang === "de" ? "de-DE" : "en-US";
}

function applyI18n() {
  document.documentElement.lang = currentLang;
  document.querySelectorAll("[data-i18n]").forEach((el) => {
    el.textContent = t(el.dataset.i18n);
  });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    el.placeholder = t(el.dataset.i18nPlaceholder);
  });
  const btn = document.getElementById("lang-toggle");
  if (btn) btn.textContent = currentLang === "de" ? "EN" : "DE";
}

async function setLanguage(lang) {
  currentLang = lang;
  applyI18n();
  try {
    await fetch("/api/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ language: lang }),
    });
  } catch (e) {
    /* Backend evtl. kurz nicht erreichbar — Sprache bleibt trotzdem lokal aktiv */
  }
  if (typeof window.refreshRepos === "function") window.refreshRepos();
}

async function initI18n() {
  try {
    const res = await fetch("/api/config");
    const cfg = await res.json();
    currentLang = cfg.language === "en" ? "en" : "de";
  } catch (e) {
    currentLang = "de";
  }
  applyI18n();
  const btn = document.getElementById("lang-toggle");
  if (btn) {
    btn.addEventListener("click", () => {
      setLanguage(currentLang === "de" ? "en" : "de");
    });
  }
  if (_i18nResolveReady) {
    _i18nResolveReady();
    _i18nResolveReady = null;
  }
}
