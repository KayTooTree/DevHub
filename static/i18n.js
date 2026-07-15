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
  },
};

let currentLang = "de";

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
}
