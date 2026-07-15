/*
 * app.js — Kernlogik des DEVHUB-Dashboards.
 *
 * Kuemmert sich um alles ausser dem eingebetteten Terminal (siehe terminal.js)
 * und der Sprachverwaltung (siehe i18n.js): Uhr, System/Netzwerk-Status,
 * Git-Repo-Tabelle, Top-Prozesse, offene Ports, Notizen und Quick-Launch.
 */

const API = "";

// ---------------------------------------------------------------------------
// Uhr
// ---------------------------------------------------------------------------

function tickClock() {
  const now = new Date();
  document.getElementById("clock").textContent = now.toLocaleTimeString(localeTag());
  document.getElementById("date").textContent = now
    .toLocaleDateString(localeTag(), { weekday: "long", year: "numeric", month: "long", day: "numeric" })
    .toUpperCase();
}
setInterval(tickClock, 1000);

// ---------------------------------------------------------------------------
// System / Netzwerk-Status
// ---------------------------------------------------------------------------

function fmtUptime(bootTime) {
  if (!bootTime) return "--";
  const secs = Date.now() / 1000 - bootTime;
  const h = Math.floor(secs / 3600);
  const m = Math.floor((secs % 3600) / 60);
  return `${h}h ${m}m`;
}

function setBar(prefix, value) {
  const v = Math.round(value || 0);
  document.getElementById(`${prefix}-bar`).style.width = v + "%";
  document.getElementById(`${prefix}-val`).textContent = v + "%";
}

async function refreshStatus() {
  try {
    const res = await fetch(`${API}/api/status`);
    const data = await res.json();
    document.getElementById("conn-status").textContent = t("footer_ok");
    document.getElementById("conn-status").className = "conn-ok";

    const sys = data.system || {};
    if (!sys.error) {
      setBar("cpu", sys.cpu_percent);
      setBar("ram", sys.ram_percent);
      setBar("disk", sys.disk_percent);
      document.getElementById("uptime").textContent = fmtUptime(sys.boot_time);
    }

    document.getElementById("local-ip").textContent = data.local_ip || "N/A";
    const pub = data.public || {};
    if (!pub.error) {
      document.getElementById("public-ip").textContent = pub.ip || "N/A";
      document.getElementById("isp").textContent = pub.isp || "N/A";
      document.getElementById("location").textContent =
        [pub.city, pub.region, pub.country].filter(Boolean).join(", ") || "N/A";
      document.getElementById("timezone").textContent = pub.timezone || "N/A";
      document.getElementById("coords").textContent =
        pub.lat && pub.lon ? `${pub.lat.toFixed(3)}, ${pub.lon.toFixed(3)}` : "N/A";
    } else {
      document.getElementById("public-ip").textContent = t("offline");
    }
  } catch (e) {
    document.getElementById("conn-status").textContent = t("footer_lost");
    document.getElementById("conn-status").className = "conn-fail";
  }
}

// ---------------------------------------------------------------------------
// Git-Repos
// ---------------------------------------------------------------------------

function repoDetail(repo) {
  switch (repo.status) {
    case "BEHIND":
      return `${repo.behind} ${t("behind_suffix")}`;
    case "AHEAD":
      return `${repo.ahead} ${t("ahead_suffix")}`;
    case "DIVERGED":
      return `${repo.ahead} ${t("diverged_label")} / ${repo.behind} ${t("behind_suffix")}`;
    case "UP_TO_DATE":
      return t("up_to_date");
    default:
      return repo.detail || repo.last_commit || "";
  }
}

async function refreshRepos() {
  try {
    const res = await fetch(`${API}/api/repos`);
    const repos = await res.json();
    const tbody = document.getElementById("repo-tbody");
    tbody.innerHTML = "";

    if (repos.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" class="loading">${t("no_repos")}</td></tr>`;
      return;
    }

    for (const repo of repos) {
      const tr = document.createElement("tr");
      const needsPull = repo.status === "BEHIND" || repo.status === "DIVERGED";
      const dirtyFlag = repo.dirty ? `<span class="dirty-flag">● ${repo.dirty} ${t("dirty_suffix")}</span>` : "";

      tr.innerHTML = `
        <td>${escapeHtml(repo.name)}</td>
        <td>${escapeHtml(repo.branch || "-")}</td>
        <td><span class="badge ${repo.status}">${repo.status.replace(/_/g, " ")}</span></td>
        <td>${escapeHtml(repoDetail(repo))}${dirtyFlag}</td>
        <td class="repo-actions">
          ${needsPull ? `<button class="btn btn-small pull-btn" data-path="${escapeHtml(repo.path)}">${t("pull")}</button>` : ""}
          <button class="btn btn-small open-btn" data-path="${escapeHtml(repo.path)}" data-tool="code">${t("code_btn")}</button>
          <button class="btn btn-small open-btn" data-path="${escapeHtml(repo.path)}" data-tool="explorer">${t("explorer_btn")}</button>
        </td>
      `;
      tbody.appendChild(tr);
    }

    document.querySelectorAll(".pull-btn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        btn.textContent = "...";
        btn.disabled = true;
        await fetch(`${API}/api/repos/pull`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ path: btn.dataset.path }),
        });
        refreshRepos();
      });
    });

    document.querySelectorAll(".open-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        fetch(`${API}/api/repos/open`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ path: btn.dataset.path, tool: btn.dataset.tool }),
        });
      });
    });
  } catch (e) {
    /* naechster Poll versucht es erneut */
  }
}
window.refreshRepos = refreshRepos;

document.getElementById("pull-all").addEventListener("click", async (e) => {
  e.target.textContent = "...";
  await fetch(`${API}/api/repos/pull_all`, { method: "POST" });
  e.target.textContent = t("pull_all");
  refreshRepos();
});

// ---------------------------------------------------------------------------
// Top-Prozesse
// ---------------------------------------------------------------------------

async function refreshProcesses() {
  try {
    const res = await fetch(`${API}/api/processes`);
    const procs = await res.json();
    const tbody = document.getElementById("proc-tbody");
    if (!procs.length) {
      tbody.innerHTML = `<tr><td colspan="3" class="loading">${t("no_processes")}</td></tr>`;
      return;
    }
    tbody.innerHTML = procs
      .map(
        (p) => `<tr><td>${escapeHtml(p.name)}</td><td>${p.cpu.toFixed(1)}</td><td>${p.mem.toFixed(1)}</td></tr>`
      )
      .join("");
  } catch (e) {
    /* still */
  }
}

// ---------------------------------------------------------------------------
// Offene Ports
// ---------------------------------------------------------------------------

async function refreshPorts() {
  try {
    const res = await fetch(`${API}/api/ports`);
    const ports = await res.json();
    const tbody = document.getElementById("ports-tbody");
    if (!ports.length) {
      tbody.innerHTML = `<tr><td colspan="3" class="loading">${t("no_ports")}</td></tr>`;
      return;
    }
    tbody.innerHTML = ports
      .map(
        (p) => `<tr><td>${p.port}</td><td>${p.pid ?? "-"}</td><td>${escapeHtml(p.process)}</td></tr>`
      )
      .join("");
  } catch (e) {
    /* still */
  }
}

// ---------------------------------------------------------------------------
// Notizen (mit Debounce-Autosave)
// ---------------------------------------------------------------------------

let notesSaveTimeout;
const notesArea = document.getElementById("notes-area");
const notesStatus = document.getElementById("notes-status");

async function loadNotes() {
  try {
    const res = await fetch(`${API}/api/notes`);
    const data = await res.json();
    notesArea.value = data.text || "";
  } catch (e) {
    /* still */
  }
}

notesArea.addEventListener("input", () => {
  clearTimeout(notesSaveTimeout);
  notesSaveTimeout = setTimeout(async () => {
    await fetch(`${API}/api/notes`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: notesArea.value }),
    });
    notesStatus.textContent = t("saved");
    notesStatus.classList.add("show");
    setTimeout(() => notesStatus.classList.remove("show"), 1200);
  }, 600);
});

// ---------------------------------------------------------------------------
// Quick Launch
// ---------------------------------------------------------------------------

async function loadLauncher() {
  try {
    const res = await fetch(`${API}/api/config`);
    const cfg = await res.json();
    const container = document.getElementById("launcher-buttons");
    const items = cfg.quick_launch || [];
    if (!items.length) {
      container.innerHTML = "";
      return;
    }
    container.innerHTML = items
      .map((item, idx) => `<button class="btn launcher-btn" data-idx="${idx}">${escapeHtml(item.label)}</button>`)
      .join("");
    container.querySelectorAll(".launcher-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        fetch(`${API}/api/launch`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ index: parseInt(btn.dataset.idx, 10) }),
        });
      });
    });
  } catch (e) {
    /* still */
  }
}

// ---------------------------------------------------------------------------
// Externes Terminal-Fenster (Fallback-Button)
// ---------------------------------------------------------------------------

document.getElementById("open-external-term").addEventListener("click", async () => {
  await fetch(`${API}/api/terminal`, { method: "POST" });
});

// ---------------------------------------------------------------------------
// Utils
// ---------------------------------------------------------------------------

function escapeHtml(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------

(async function init() {
  await initI18n();
  tickClock();
  refreshStatus();
  refreshRepos();
  refreshProcesses();
  refreshPorts();
  loadNotes();
  loadLauncher();

  setInterval(refreshStatus, 4000);
  setInterval(refreshRepos, 15000);
  setInterval(refreshProcesses, 5000);
  setInterval(refreshPorts, 10000);
})();
