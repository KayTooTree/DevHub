/*
 * panel.js — Server-Monitor-Panel ("Kuechenmonitor").
 *
 * Zeigt Notizen/Changelogs und Aktivitaet live an, komplett unabhaengig
 * davon ob gerade ein DEVHUB Client verbunden ist. Der API-Key wird EINMAL
 * eingegeben (oder per #token=... in der URL mitgegeben) und dann optional
 * in diesem Browser gemerkt -- Datenabfragen laufen ganz normal ueber die
 * authentifizierten Agent-Endpunkte (/status, /notes, /logs, /repos).
 */

const STORAGE_KEY = "devhub_panel_token";
let apiToken = null;
let lastSeenNoteTs = 0;
let firstNotesLoad = true;

// ---------------------------------------------------------------------------
// Token-Beschaffung
// ---------------------------------------------------------------------------

function getTokenFromHash() {
  const match = window.location.hash.match(/token=([^&]+)/);
  return match ? decodeURIComponent(match[1]) : null;
}

function initToken() {
  const hashToken = getTokenFromHash();
  if (hashToken) {
    apiToken = hashToken;
    // Token nicht dauerhaft sichtbar in der Adressleiste stehen lassen
    history.replaceState(null, "", window.location.pathname);
    localStorage.setItem(STORAGE_KEY, apiToken);
    return true;
  }

  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored) {
    apiToken = stored;
    return true;
  }

  return false;
}

function showTokenGate(errorMsg) {
  const gate = document.getElementById("token-gate");
  gate.classList.remove("hidden");
  const errEl = document.getElementById("token-error");
  if (errorMsg) {
    errEl.textContent = errorMsg;
    errEl.classList.remove("hidden");
  } else {
    errEl.classList.add("hidden");
  }
}

function hideTokenGate() {
  document.getElementById("token-gate").classList.add("hidden");
}

document.getElementById("token-submit").addEventListener("click", () => {
  const value = document.getElementById("token-input").value.trim();
  if (!value) return;
  apiToken = value;
  if (document.getElementById("token-remember").checked) {
    localStorage.setItem(STORAGE_KEY, value);
  }
  hideTokenGate();
  refreshAll();
});

document.getElementById("token-input").addEventListener("keydown", (e) => {
  if (e.key === "Enter") document.getElementById("token-submit").click();
});

// ---------------------------------------------------------------------------
// Uhr
// ---------------------------------------------------------------------------

function tickClock() {
  document.getElementById("monitor-clock").textContent = new Date().toLocaleTimeString("de-DE");
}
setInterval(tickClock, 1000);
tickClock();

// ---------------------------------------------------------------------------
// Fetch-Helper mit Auth-Header
// ---------------------------------------------------------------------------

async function authFetch(path) {
  const res = await fetch(path, {
    headers: { Authorization: `Bearer ${apiToken}` },
  });
  if (res.status === 401) {
    localStorage.removeItem(STORAGE_KEY);
    apiToken = null;
    showTokenGate("API-Key ungültig. Bitte erneut eingeben.");
    throw new Error("unauthorized");
  }
  return res.json();
}

function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function fmtTimestamp(ts) {
  if (!ts) return "--";
  return new Date(ts * 1000).toLocaleString("de-DE");
}

function fmtUptime(bootTime) {
  if (!bootTime) return "--";
  const secs = Date.now() / 1000 - bootTime;
  const h = Math.floor(secs / 3600);
  const m = Math.floor((secs % 3600) / 60);
  return `${h}h ${m}m`;
}

// ---------------------------------------------------------------------------
// Health (kein Auth noetig -- Servername im Header)
// ---------------------------------------------------------------------------

async function refreshHealth() {
  try {
    const res = await fetch("/health");
    const data = await res.json();
    document.getElementById("server-name").textContent = data.name || "DEVHUB";
    document.getElementById("conn-dot").classList.add("online");
    document.getElementById("conn-text").textContent = "ONLINE";
  } catch (e) {
    document.getElementById("conn-dot").classList.remove("online");
    document.getElementById("conn-text").textContent = "OFFLINE";
  }
}

// ---------------------------------------------------------------------------
// Status
// ---------------------------------------------------------------------------

async function refreshStatus() {
  try {
    const data = await authFetch("/status");
    document.getElementById("monitor-hostname").textContent = data.hostname || "--";
    const sys = data.system || {};
    document.getElementById("monitor-cpu").textContent = Math.round(sys.cpu_percent || 0) + "%";
    document.getElementById("monitor-ram").textContent = Math.round(sys.ram_percent || 0) + "%";
    document.getElementById("monitor-uptime").textContent = fmtUptime(sys.uptime_seconds || sys.boot_time);
  } catch (e) {
    /* Fehler wurde bereits behandelt (z.B. Token-Gate) */
  }
}

async function refreshRepos() {
  try {
    const repos = await authFetch("/repos");
    const behind = repos.filter((r) => r.status === "BEHIND" || r.status === "DIVERGED").length;
    document.getElementById("monitor-repos").textContent =
      behind > 0 ? `${behind} REPO(S) HINTER REMOTE` : "ALLE REPOS AKTUELL";
  } catch (e) {
    /* still */
  }
}

// ---------------------------------------------------------------------------
// Notizen-Board
// ---------------------------------------------------------------------------

async function refreshNotes() {
  try {
    const notes = await authFetch("/notes");
    const board = document.getElementById("notes-board");

    if (!notes.length) {
      board.innerHTML = `<div class="board-empty">Noch keine Notizen</div>`;
      firstNotesLoad = false;
      return;
    }

    const sorted = [...notes].reverse();
    const maxTs = Math.max(...notes.map((n) => n.ts || 0));

    board.innerHTML = sorted
      .map((n) => {
        const isNew = !firstNotesLoad && n.ts > lastSeenNoteTs;
        return `<div class="note-card ${isNew ? "is-new" : ""}">
          <div class="note-meta"><span class="note-author">${escapeHtml(n.author)}</span><span>${fmtTimestamp(n.ts)}</span></div>
          <div class="note-text">${escapeHtml(n.text)}</div>
        </div>`;
      })
      .join("");

    lastSeenNoteTs = maxTs;
    firstNotesLoad = false;
  } catch (e) {
    /* still */
  }
}

// ---------------------------------------------------------------------------
// Aktivitaets-Log
// ---------------------------------------------------------------------------

async function refreshLogs() {
  try {
    const logs = await authFetch("/logs");
    const board = document.getElementById("log-board");

    if (!logs.length) {
      board.innerHTML = `<div class="board-empty">Noch keine Aktivität</div>`;
      return;
    }

    board.innerHTML = logs
      .slice(0, 40)
      .map(
        (l) => `<div class="log-entry">
          <span class="log-time">${fmtTimestamp(l.ts)}</span>
          <span class="log-user">${escapeHtml(l.username)}</span> <span class="log-action">${escapeHtml(l.action)}</span>
          ${l.detail ? " — " + escapeHtml(l.detail) : ""}
        </div>`
      )
      .join("");
  } catch (e) {
    /* still */
  }
}

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------

async function refreshAll() {
  if (!apiToken) return;
  await Promise.all([refreshStatus(), refreshRepos(), refreshNotes(), refreshLogs()]);
}

(function init() {
  refreshHealth();
  setInterval(refreshHealth, 20000);

  if (initToken()) {
    hideTokenGate();
    refreshAll();
  } else {
    showTokenGate();
  }

  setInterval(refreshAll, 5000);
})();
