/*
 * servers.js — "Remote Servers": verlinkte DEVHUB-Agents auf anderen
 * Rechnern verwalten und über ein Panel mit 4 Reitern (Leistung, Repos,
 * Notizen, Logs) bedienen.
 *
 * Alle Aufrufe gehen an den lokalen Client-Backend-Proxy (/api/servers/...),
 * niemals direkt an den Agent -- der API-Key jedes Servers bleibt serverseitig.
 */

const SERVERS_API = "/api/servers";

const modalOverlay = document.getElementById("modal-overlay");
const modalBox = document.getElementById("modal-box");

function showModal(html) {
  modalBox.innerHTML = html;
  modalOverlay.classList.remove("hidden");
}

function hideModal() {
  modalOverlay.classList.add("hidden");
  modalBox.innerHTML = "";
}

modalOverlay.addEventListener("click", (e) => {
  if (e.target === modalOverlay) hideModal();
});

function fmtUptimeSeconds(bootTime) {
  if (!bootTime) return "--";
  const secs = Date.now() / 1000 - bootTime;
  const h = Math.floor(secs / 3600);
  const m = Math.floor((secs % 3600) / 60);
  return `${h}h ${m}m`;
}

function fmtTimestamp(ts) {
  if (!ts) return "--";
  return new Date(ts * 1000).toLocaleString(localeTag());
}

// ---------------------------------------------------------------------------
// Server-Karten
// ---------------------------------------------------------------------------

async function loadServerList() {
  const container = document.getElementById("server-cards");
  try {
    const res = await fetch(SERVERS_API);
    const servers = await res.json();

    if (!servers.length) {
      container.innerHTML = `<span class="loading">${t("no_servers")}</span>`;
      return;
    }

    container.innerHTML = servers
      .map(
        (s) => `
      <div class="server-card" data-name="${escapeHtml(s.name)}">
        <div class="server-card-header">
          <span class="server-card-name">${escapeHtml(s.name)}</span>
          <button class="server-card-remove" data-name="${escapeHtml(s.name)}" title="${t("remove_server")}">×</button>
        </div>
        <div class="server-card-row"><span>${escapeHtml(s.host)}:${s.port}</span>
          <span class="server-status-badge" data-field="status">...</span>
        </div>
        <div class="server-card-row"><span>${t("server_uptime_label")}</span><span data-field="uptime">--</span></div>
        <div class="server-card-footer">
          <button class="btn btn-small open-panel-btn" data-name="${escapeHtml(s.name)}">${t("open_panel")}</button>
        </div>
      </div>`
      )
      .join("");

    container.querySelectorAll(".open-panel-btn").forEach((btn) => {
      btn.addEventListener("click", () => openServerPanel(btn.dataset.name));
    });
    container.querySelectorAll(".server-card-remove").forEach((btn) => {
      btn.addEventListener("click", () => removeServer(btn.dataset.name));
    });

    servers.forEach((s) => refreshServerCard(s.name));
  } catch (e) {
    container.innerHTML = `<span class="loading">${t("connection_failed")}</span>`;
  }
}

async function refreshServerCard(name) {
  const card = document.querySelector(`.server-card[data-name="${cssEscape(name)}"]`);
  if (!card) return;
  const statusEl = card.querySelector('[data-field="status"]');
  const uptimeEl = card.querySelector('[data-field="uptime"]');

  try {
    const healthRes = await fetch(`${SERVERS_API}/${encodeURIComponent(name)}/health`);
    const health = await healthRes.json();

    if (!health.online) {
      statusEl.textContent = t("server_offline");
      statusEl.className = "server-status-badge offline";
      uptimeEl.textContent = "--";
      return;
    }
    statusEl.textContent = t("server_online");
    statusEl.className = "server-status-badge online";

    const statusRes = await fetch(`${SERVERS_API}/${encodeURIComponent(name)}/status`);
    const wrapped = await statusRes.json();
    const sys = wrapped.data?.system;
    uptimeEl.textContent = sys ? fmtUptimeSeconds(sys.boot_time) : "--";
  } catch (e) {
    statusEl.textContent = t("server_offline");
    statusEl.className = "server-status-badge offline";
  }
}

function cssEscape(str) {
  return String(str).replace(/["\\]/g, "\\$&");
}

async function removeServer(name) {
  if (!confirm(t("confirm_remove_server"))) return;
  await fetch(`${SERVERS_API}/${encodeURIComponent(name)}`, { method: "DELETE" });
  loadServerList();
}

document.getElementById("add-server-btn").addEventListener("click", openAddServerModal);

// ---------------------------------------------------------------------------
// "Server hinzufügen"-Modal
// ---------------------------------------------------------------------------

function openAddServerModal() {
  showModal(`
    <div class="modal-header">
      <span class="modal-title">${t("modal_add_server_title")}</span>
      <button class="modal-close" id="modal-close-btn">×</button>
    </div>
    <div class="modal-body">
      <div class="form-row"><label>${t("field_name")}</label><input id="new-server-name" type="text" placeholder="z.B. VPS Frankfurt"></div>
      <div class="form-row"><label>${t("field_host")}</label><input id="new-server-host" type="text" placeholder="10.0.0.5"></div>
      <div class="form-row"><label>${t("field_port")}</label><input id="new-server-port" type="number" value="8060"></div>
      <div class="form-row"><label>${t("field_token")}</label><input id="new-server-token" type="text" placeholder="aus der Agent-Konsole kopieren"></div>
      <div class="form-error hidden" id="add-server-error"></div>
      <div class="form-actions">
        <button class="btn btn-small" id="cancel-add-server">${t("cancel")}</button>
        <button class="btn btn-small" id="submit-add-server">${t("save")}</button>
      </div>
    </div>
  `);
  document.getElementById("modal-close-btn").addEventListener("click", hideModal);
  document.getElementById("cancel-add-server").addEventListener("click", hideModal);
  document.getElementById("submit-add-server").addEventListener("click", submitAddServer);
}

async function submitAddServer() {
  const name = document.getElementById("new-server-name").value.trim();
  const host = document.getElementById("new-server-host").value.trim();
  const port = parseInt(document.getElementById("new-server-port").value, 10);
  const token = document.getElementById("new-server-token").value.trim();
  const errorEl = document.getElementById("add-server-error");

  if (!name || !host || !port || !token) {
    errorEl.textContent = t("all_fields_required");
    errorEl.classList.remove("hidden");
    return;
  }

  const res = await fetch(SERVERS_API, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, host, port, token }),
  });
  const data = await res.json();
  if (!data.ok) {
    errorEl.textContent = data.error || t("connection_failed");
    errorEl.classList.remove("hidden");
    return;
  }
  hideModal();
  loadServerList();
}

// ---------------------------------------------------------------------------
// Server-Panel (4 Reiter: Leistung, Repos, Notizen, Logs)
// ---------------------------------------------------------------------------

let currentServerName = null;
let currentServerTab = "performance";

function openServerPanel(name) {
  currentServerName = name;
  currentServerTab = "performance";
  showModal(`
    <div class="modal-header">
      <span class="modal-title">${escapeHtml(name)}</span>
      <button class="modal-close" id="modal-close-btn">×</button>
    </div>
    <div class="server-panel-tabs">
      <button class="server-panel-tab" data-tab="performance">${t("tab_performance")}</button>
      <button class="server-panel-tab" data-tab="repos">${t("tab_repos")}</button>
      <button class="server-panel-tab" data-tab="notes">${t("tab_notes")}</button>
      <button class="server-panel-tab" data-tab="logs">${t("tab_logs")}</button>
    </div>
    <div class="server-panel-tab-content" id="server-panel-content"></div>
  `);
  document.getElementById("modal-close-btn").addEventListener("click", hideModal);
  modalBox.querySelectorAll(".server-panel-tab").forEach((btn) => {
    btn.addEventListener("click", () => switchServerTab(btn.dataset.tab));
  });
  switchServerTab("performance");
}

function switchServerTab(tab) {
  currentServerTab = tab;
  modalBox.querySelectorAll(".server-panel-tab").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.tab === tab);
  });
  const content = document.getElementById("server-panel-content");
  content.innerHTML = `<span class="loading">...</span>`;

  if (tab === "performance") loadPerformanceTab(currentServerName, content);
  else if (tab === "repos") loadReposTab(currentServerName, content);
  else if (tab === "notes") loadNotesTab(currentServerName, content);
  else if (tab === "logs") loadLogsTab(currentServerName, content);
}

// ---- Tab: Leistung ----

async function loadPerformanceTab(name, content) {
  const base = `${SERVERS_API}/${encodeURIComponent(name)}`;
  try {
    const [statusRes, procRes, portsRes, dockerRes] = await Promise.all([
      fetch(`${base}/status`),
      fetch(`${base}/processes`),
      fetch(`${base}/ports`),
      fetch(`${base}/docker`),
    ]);
    const status = await statusRes.json();
    const procs = await procRes.json();
    const ports = await portsRes.json();
    const docker = await dockerRes.json();

    if (status.error && !status.data) {
      content.innerHTML = `<div class="form-error">${escapeHtml(status.error)}</div>`;
      return;
    }

    const sys = status.data?.system || {};
    const cpu = Math.round(sys.cpu_percent || 0);
    const ram = Math.round(sys.ram_percent || 0);
    const disk = Math.round(sys.disk_percent || 0);

    let html = `
      <div class="kv"><span>${t("server_hostname_label")}</span><span class="val">${escapeHtml(status.data?.hostname || "--")}</span></div>
      <div class="kv"><span>${t("server_os_label")}</span><span class="val">${escapeHtml(status.data?.os || "--")}</span></div>
      <div class="kv"><span>${t("server_uptime_label")}</span><span class="val">${fmtUptimeSeconds(sys.boot_time)}</span></div>
      <div style="height:14px"></div>
      <div class="stat-row"><span class="stat-label">CPU</span><div class="bar"><div class="bar-fill" style="width:${cpu}%"></div></div><span class="stat-val">${cpu}%</span></div>
      <div class="stat-row"><span class="stat-label">${t("memory")}</span><div class="bar"><div class="bar-fill" style="width:${ram}%"></div></div><span class="stat-val">${ram}%</span></div>
      <div class="stat-row"><span class="stat-label">${t("disk")}</span><div class="bar"><div class="bar-fill" style="width:${disk}%"></div></div><span class="stat-val">${disk}%</span></div>
    `;

    const procList = procs.data || [];
    html += `<div style="height:10px"></div><table class="mini-table"><thead><tr><th>${t("th_process")}</th><th>${t("th_cpu")}</th><th>${t("th_mem")}</th></tr></thead><tbody>`;
    html += procList.length
      ? procList.map((p) => `<tr><td>${escapeHtml(p.name)}</td><td>${p.cpu.toFixed(1)}</td><td>${p.mem.toFixed(1)}</td></tr>`).join("")
      : `<tr><td colspan="3" class="loading">${t("no_processes")}</td></tr>`;
    html += `</tbody></table>`;

    const portList = ports.data || [];
    html += `<div style="height:10px"></div><table class="mini-table"><thead><tr><th>${t("th_port")}</th><th>${t("th_pid")}</th><th>${t("th_process")}</th></tr></thead><tbody>`;
    html += portList.length
      ? portList.map((p) => `<tr><td>${p.port}</td><td>${p.pid ?? "-"}</td><td>${escapeHtml(p.process)}</td></tr>`).join("")
      : `<tr><td colspan="3" class="loading">${t("no_ports")}</td></tr>`;
    html += `</tbody></table>`;

    const dockerData = docker.data;
    html += `<div style="height:10px"></div><table class="mini-table"><thead><tr><th>${t("th_container")}</th><th>${t("th_status")}</th><th>${t("th_image")}</th></tr></thead><tbody>`;
    if (!dockerData || !dockerData.available) {
      html += `<tr><td colspan="3" class="loading">${t("docker_unavailable")}</td></tr>`;
    } else if (!dockerData.containers.length) {
      html += `<tr><td colspan="3" class="loading">${t("no_containers")}</td></tr>`;
    } else {
      html += dockerData.containers
        .map((c) => {
          const up = /up/i.test(c.status);
          return `<tr><td>${escapeHtml(c.name)}</td><td class="${up ? "docker-up" : "docker-down"}">${escapeHtml(c.status)}</td><td>${escapeHtml(c.image)}</td></tr>`;
        })
        .join("");
    }
    html += `</tbody></table>`;

    content.innerHTML = html;
  } catch (e) {
    content.innerHTML = `<div class="form-error">${t("connection_failed")}</div>`;
  }
}

// ---- Tab: Repos ----

async function loadReposTab(name, content) {
  const base = `${SERVERS_API}/${encodeURIComponent(name)}`;
  try {
    const res = await fetch(`${base}/repos`);
    const wrapped = await res.json();
    const repos = wrapped.data || [];

    if (wrapped.error && !repos.length) {
      content.innerHTML = `<div class="form-error">${escapeHtml(wrapped.error)}</div>`;
      return;
    }
    if (!repos.length) {
      content.innerHTML = `<span class="loading">${t("no_repos")}</span>`;
      return;
    }

    let html = `<div class="form-actions" style="justify-content:flex-start;margin-bottom:12px;">
      <button class="btn btn-small" id="remote-pull-all">${t("pull_all")}</button>
    </div>`;
    html += `<table class="repo-table"><thead><tr>
      <th>${t("th_repo")}</th><th>${t("th_branch")}</th><th>${t("th_status")}</th><th>${t("th_detail")}</th><th>${t("th_actions")}</th>
    </tr></thead><tbody>`;

    for (const repo of repos) {
      const needsPull = repo.status === "BEHIND" || repo.status === "DIVERGED";
      let detail = repo.detail || repo.last_commit || "";
      if (repo.status === "UP_TO_DATE") detail = t("up_to_date");
      else if (repo.status === "BEHIND") detail = `${repo.behind} ${t("behind_suffix")}`;
      else if (repo.status === "AHEAD") detail = `${repo.ahead} ${t("ahead_suffix")}`;
      const dirtyFlag = repo.dirty ? `<span class="dirty-flag">● ${repo.dirty} ${t("dirty_suffix")}</span>` : "";

      html += `<tr>
        <td>${escapeHtml(repo.name)}</td>
        <td>${escapeHtml(repo.branch || "-")}</td>
        <td><span class="badge ${repo.status}">${repo.status.replace(/_/g, " ")}</span></td>
        <td>${escapeHtml(detail)}${dirtyFlag}</td>
        <td>${needsPull ? `<button class="btn btn-small remote-pull-btn" data-path="${escapeHtml(repo.path)}">${t("pull")}</button>` : ""}</td>
      </tr>`;
    }
    html += `</tbody></table>`;
    content.innerHTML = html;

    document.getElementById("remote-pull-all").addEventListener("click", async (e) => {
      e.target.textContent = "...";
      await fetch(`${base}/repos/pull_all`, { method: "POST" });
      loadReposTab(name, content);
    });
    content.querySelectorAll(".remote-pull-btn").forEach((btn) => {
      btn.addEventListener("click", async () => {
        btn.textContent = "...";
        btn.disabled = true;
        await fetch(`${base}/repos/pull`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ path: btn.dataset.path }),
        });
        loadReposTab(name, content);
      });
    });
  } catch (e) {
    content.innerHTML = `<div class="form-error">${t("connection_failed")}</div>`;
  }
}

// ---- Tab: Notizen ----

async function loadNotesTab(name, content) {
  const base = `${SERVERS_API}/${encodeURIComponent(name)}`;
  try {
    const res = await fetch(`${base}/notes`);
    const wrapped = await res.json();
    const notes = wrapped.data || [];

    let html = "";
    if (!notes.length) {
      html += `<span class="loading">${t("no_notes")}</span>`;
    } else {
      html += [...notes]
        .reverse()
        .map(
          (n) => `<div class="note-item">
            <span class="note-author">${escapeHtml(n.author)}</span><span class="note-time">${fmtTimestamp(n.ts)}</span>
            <div class="note-text">${escapeHtml(n.text)}</div>
          </div>`
        )
        .join("");
    }
    html += `<div class="note-compose">
      <textarea id="new-note-text" placeholder="${t("note_placeholder")}"></textarea>
      <button class="btn btn-small" id="send-note-btn">${t("send_note")}</button>
    </div>`;
    content.innerHTML = html;

    document.getElementById("send-note-btn").addEventListener("click", async () => {
      const textarea = document.getElementById("new-note-text");
      const text = textarea.value.trim();
      if (!text) return;
      await fetch(`${base}/notes`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      loadNotesTab(name, content);
    });
  } catch (e) {
    content.innerHTML = `<div class="form-error">${t("connection_failed")}</div>`;
  }
}

// ---- Tab: Logs ----

async function loadLogsTab(name, content) {
  const base = `${SERVERS_API}/${encodeURIComponent(name)}`;
  try {
    const res = await fetch(`${base}/logs`);
    const wrapped = await res.json();
    const logs = wrapped.data || [];

    if (!logs.length) {
      content.innerHTML = `<span class="loading">${t("no_logs")}</span>`;
      return;
    }

    content.innerHTML = logs
      .map(
        (l) => `<div class="log-item">
          <span class="log-time">${fmtTimestamp(l.ts)}</span>
          <span class="log-user">${escapeHtml(l.username)}</span>
          <span class="log-action">${escapeHtml(l.action)}</span>
          <span class="log-detail">${escapeHtml(l.detail || "")}</span>
        </div>`
      )
      .join("");
  } catch (e) {
    content.innerHTML = `<div class="form-error">${t("connection_failed")}</div>`;
  }
}

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------

(async function initServers() {
  await window.i18nReadyPromise;
  loadServerList();
  setInterval(loadServerList, 20000);
})();
