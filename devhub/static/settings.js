/*
 * settings.js — Setup-Wizard beim ersten Start + Einstellungen-Modal.
 *
 * Nutzt dieselbe Modal-Infrastruktur wie servers.js (showModal/hideModal/
 * modalBox), damit nur ein einheitliches Overlay-System existiert.
 *
 * Beim allerersten Start (config.onboarding_complete === false) oeffnet
 * sich dieses Modal automatisch: Anzeigename setzen, optional gleich
 * Repos eintragen. Danach jederzeit ueber das Zahnrad-Symbol im Header
 * erreichbar, um Name/Repos spaeter zu aendern.
 */

let currentSettingsTab = "profile";
let isOnboarding = false;
let accountPollInterval = null;

function clearAccountPoll() {
  if (accountPollInterval) {
    clearInterval(accountPollInterval);
    accountPollInterval = null;
  }
}

function openSettings(onboarding = false) {
  isOnboarding = onboarding;
  currentSettingsTab = onboarding ? "account" : "profile";
  showModal(`
    <div class="modal-header">
      <span class="modal-title">${onboarding ? t("welcome_title") : t("settings_title")}</span>
      ${onboarding ? "" : '<button class="modal-close" id="modal-close-btn">×</button>'}
    </div>
    ${onboarding ? `<div class="settings-welcome-hint">${t("welcome_hint")}</div>` : ""}
    <div class="server-panel-tabs">
      <button class="server-panel-tab" data-tab="account">${t("tab_account")}</button>
      <button class="server-panel-tab" data-tab="profile">${t("tab_profile")}</button>
      <button class="server-panel-tab" data-tab="repos">${t("tab_repos")}</button>
      <button class="server-panel-tab" data-tab="discord">${t("tab_discord_rpc")}</button>
      <button class="server-panel-tab" data-tab="feedback">${t("tab_feedback")}</button>
    </div>
    <div class="server-panel-tab-content" id="settings-tab-content"></div>
  `);
  if (!onboarding) {
    document.getElementById("modal-close-btn").addEventListener("click", () => {
      clearAccountPoll();
      hideModal();
    });
  }
  modalBox.querySelectorAll(".server-panel-tab").forEach((btn) => {
    btn.addEventListener("click", () => switchSettingsTab(btn.dataset.tab));
  });
  switchSettingsTab(currentSettingsTab);
}

function switchSettingsTab(tab) {
  clearAccountPoll();
  currentSettingsTab = tab;
  modalBox.querySelectorAll(".server-panel-tab").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.tab === tab);
  });
  const content = document.getElementById("settings-tab-content");
  content.innerHTML = `<span class="loading">...</span>`;

  if (tab === "account") loadAccountTab(content);
  else if (tab === "profile") loadProfileTab(content);
  else if (tab === "repos") loadReposConfigTab(content);
  else if (tab === "discord") loadDiscordTab(content);
  else if (tab === "feedback") loadFeedbackTab(content);
}

// ---- Tab: Discord-Konto ----

async function loadAccountTab(content) {
  let cfg;
  try {
    cfg = await (await fetch(`${API}/api/config`)).json();
  } catch (e) {
    content.innerHTML = `<div class="form-error">${t("settings_load_error")}</div>`;
    return;
  }

  const identity = cfg.discord_identity;

  if (identity) {
    const roles = (identity.roles || []).map((r) => `<span class="gh-badge">${escapeHtml(r)}</span>`).join(" ");
    content.innerHTML = `
      <div class="account-card">
        <img class="account-avatar" src="${escapeHtml(identity.avatar_url)}" alt="Avatar">
        <div class="account-info">
          <div class="account-name">${escapeHtml(identity.display_name)}</div>
          <div class="account-username">${escapeHtml(identity.username)}</div>
          <div class="account-roles">${roles}</div>
        </div>
      </div>
      <p class="settings-hint">${t("account_linked_hint")}</p>
      <div class="form-actions">
        <button class="btn" id="account-unlink-btn">${t("unlink_account")}</button>
        ${isOnboarding ? `<button class="btn" id="account-continue-btn">${t("finish_setup")}</button>` : ""}
      </div>
    `;
    document.getElementById("account-unlink-btn").addEventListener("click", async () => {
      await fetch(`${API}/api/discord/unlink`, { method: "POST" });
      loadAccountTab(content);
    });
    if (isOnboarding) {
      document.getElementById("account-continue-btn").addEventListener("click", () => switchSettingsTab("profile"));
    }
    return;
  }

  content.innerHTML = `
    <p class="settings-hint">${t("account_hint")}</p>
    <div class="form-actions">
      <button class="btn" id="account-link-start-btn">${t("link_discord")}</button>
      ${isOnboarding ? `<button class="btn" id="account-skip-btn">${t("skip_for_now")}</button>` : ""}
    </div>
    <div id="account-link-progress"></div>
  `;

  if (isOnboarding) {
    document.getElementById("account-skip-btn").addEventListener("click", () => switchSettingsTab("profile"));
  }

  document.getElementById("account-link-start-btn").addEventListener("click", async () => {
    const progress = document.getElementById("account-link-progress");
    progress.innerHTML = `<p class="settings-hint">${t("generating_code")}</p>`;
    const res = await fetch(`${API}/api/discord/link/start`, { method: "POST" });
    const data = await res.json();
    const code = data.code;

    progress.innerHTML = `
      <div class="verify-code-box">${escapeHtml(code)}</div>
      <p class="settings-hint">${t("verify_instructions")}</p>
      <p class="settings-hint verify-waiting">${t("waiting_for_verify")}</p>
    `;

    clearAccountPoll();
    accountPollInterval = setInterval(async () => {
      const statusRes = await fetch(`${API}/api/discord/link/status`);
      const status = await statusRes.json();
      if (status.linked) {
        clearAccountPoll();
        loadAccountTab(content);
      } else if (!status.waiting && status.error) {
        clearAccountPoll();
        progress.innerHTML = `<div class="form-error">${escapeHtml(status.error)}</div>`;
      }
    }, 2000);
  });
}

// ---- Tab: Profil ----

async function loadProfileTab(content) {
  let cfg;
  try {
    cfg = await (await fetch(`${API}/api/config`)).json();
  } catch (e) {
    content.innerHTML = `<div class="form-error">${t("settings_load_error")}</div>`;
    return;
  }

  content.innerHTML = `
    <div class="form-row">
      <label>${t("field_display_name")}</label>
      <input id="settings-operator-name" type="text" value="${escapeHtml(cfg.operator_name || "")}" placeholder="${t("field_display_name_placeholder")}">
    </div>
    <p class="settings-hint">${t("display_name_hint")}</p>
    <div id="settings-profile-error" class="form-error hidden"></div>
    <div class="form-actions">
      ${isOnboarding ? `<button class="btn" id="settings-skip-btn">${t("skip_for_now")}</button>` : ""}
      <button class="btn" id="settings-save-profile-btn">${isOnboarding ? t("finish_setup") : t("save")}</button>
    </div>
  `;

  if (isOnboarding) {
    document.getElementById("settings-skip-btn").addEventListener("click", async () => {
      await fetch(`${API}/api/config`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ onboarding_complete: true }),
      });
      hideModal();
    });
  }

  document.getElementById("settings-save-profile-btn").addEventListener("click", async () => {
    const name = document.getElementById("settings-operator-name").value.trim();
    const errEl = document.getElementById("settings-profile-error");
    if (!name) {
      errEl.textContent = t("display_name_required");
      errEl.classList.remove("hidden");
      return;
    }
    errEl.classList.add("hidden");
    await fetch(`${API}/api/config`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ operator_name: name, onboarding_complete: true }),
    });
    if (isOnboarding) {
      hideModal();
    } else {
      switchSettingsTab("profile");
    }
  });
}

// ---- Tab: Repos ----

async function loadReposConfigTab(content) {
  let repos;
  try {
    repos = await (await fetch(`${API}/api/repos/config`)).json();
  } catch (e) {
    content.innerHTML = `<div class="form-error">${t("settings_load_error")}</div>`;
    return;
  }

  const rows = repos.length
    ? repos
        .map(
          (r) => `<div class="settings-repo-row">
            <div class="settings-repo-info">
              <span class="settings-repo-name">${escapeHtml(r.name)}</span>
              <span class="settings-repo-path">${escapeHtml(r.path)}</span>
              ${r.github ? `<span class="gh-badge">${escapeHtml(r.github)}</span>` : ""}
            </div>
            <button class="btn btn-small settings-repo-remove" data-name="${escapeHtml(r.name)}">×</button>
          </div>`
        )
        .join("")
    : `<div class="settings-hint">${t("no_repos_yet")}</div>`;

  content.innerHTML = `
    <div class="settings-repo-list">${rows}</div>
    <div class="settings-divider"></div>
    <div class="form-row">
      <label>${t("field_repo_name")}</label>
      <input id="settings-new-repo-name" type="text" placeholder="${t("field_repo_name_placeholder")}">
    </div>
    <div class="form-row">
      <label>${t("field_repo_path")}</label>
      <input id="settings-new-repo-path" type="text" placeholder="${t("field_repo_path_placeholder")}">
    </div>
    <div class="form-row">
      <label>${t("field_repo_github")}</label>
      <input id="settings-new-repo-github" type="text" placeholder="${t("field_repo_github_placeholder")}">
    </div>
    <div id="settings-repo-error" class="form-error hidden"></div>
    <div class="form-actions">
      ${isOnboarding ? `<button class="btn" id="settings-repos-done-btn">${t("finish_setup")}</button>` : ""}
      <button class="btn" id="settings-add-repo-btn">${t("add_repo")}</button>
    </div>
  `;

  content.querySelectorAll(".settings-repo-remove").forEach((btn) => {
    btn.addEventListener("click", async () => {
      await fetch(`${API}/api/repos/config/${encodeURIComponent(btn.dataset.name)}`, { method: "DELETE" });
      loadReposConfigTab(content);
      if (typeof window.refreshRepos === "function") window.refreshRepos();
    });
  });

  if (isOnboarding) {
    document.getElementById("settings-repos-done-btn").addEventListener("click", async () => {
      await fetch(`${API}/api/config`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ onboarding_complete: true }),
      });
      hideModal();
    });
  }

  document.getElementById("settings-add-repo-btn").addEventListener("click", async () => {
    const name = document.getElementById("settings-new-repo-name").value.trim();
    const path = document.getElementById("settings-new-repo-path").value.trim();
    const github = document.getElementById("settings-new-repo-github").value.trim();
    const errEl = document.getElementById("settings-repo-error");

    if (!name || !path) {
      errEl.textContent = t("repo_name_path_required");
      errEl.classList.remove("hidden");
      return;
    }

    const res = await fetch(`${API}/api/repos/config`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, path, github }),
    });
    const data = await res.json();
    if (!data.ok) {
      errEl.textContent = data.error || t("settings_load_error");
      errEl.classList.remove("hidden");
      return;
    }
    loadReposConfigTab(content);
    if (typeof window.refreshRepos === "function") window.refreshRepos();
  });
}

// ---- Tab: Discord RPC ----

async function loadDiscordTab(content) {
  let cfg;
  try {
    cfg = await (await fetch(`${API}/api/config`)).json();
  } catch (e) {
    content.innerHTML = `<div class="form-error">${t("settings_load_error")}</div>`;
    return;
  }
  const d = cfg.discord_rpc || {};

  content.innerHTML = `
    <p class="settings-hint">${t("discord_hint")}</p>
    <label class="toggle-row">
      <span class="toggle-label-text">${t("field_discord_enabled")}</span>
      <span class="toggle-switch">
        <input type="checkbox" id="discord-enabled" ${d.enabled ? "checked" : ""}>
        <span class="toggle-slider"></span>
      </span>
    </label>
    <div class="form-row">
      <label>${t("field_discord_client_id")}</label>
      <input id="discord-client-id" type="text" value="${escapeHtml(d.client_id || "")}" placeholder="${t("field_discord_client_id_placeholder")}">
    </div>
    <div class="form-row">
      <label>${t("field_discord_details")}</label>
      <input id="discord-details" type="text" value="${escapeHtml(d.details || "")}" placeholder="Powered by DevHub">
    </div>
    <label class="toggle-row">
      <span class="toggle-label-text">${t("field_discord_live_status")}</span>
      <span class="toggle-switch">
        <input type="checkbox" id="discord-live-status" ${d.show_live_status ? "checked" : ""}>
        <span class="toggle-slider"></span>
      </span>
    </label>
    <div class="form-row">
      <label>${t("field_discord_state")}</label>
      <input id="discord-state" type="text" value="${escapeHtml(d.state || "")}" placeholder="${t("field_discord_state_placeholder")}">
    </div>
    <div class="form-row">
      <label>${t("field_discord_image_key")}</label>
      <input id="discord-image-key" type="text" value="${escapeHtml(d.large_image_key || "")}" placeholder="${t("field_discord_image_key_placeholder")}">
    </div>
    <div class="form-row">
      <label>${t("field_discord_image_text")}</label>
      <input id="discord-image-text" type="text" value="${escapeHtml(d.large_image_text || "")}">
    </div>
    <p class="settings-hint">${t("discord_button_hint")}</p>
    <div class="form-actions">
      <button class="btn" id="settings-save-discord-btn">${t("save")}</button>
    </div>
  `;

  document.getElementById("settings-save-discord-btn").addEventListener("click", async () => {
    const updated = {
      ...d,
      enabled: document.getElementById("discord-enabled").checked,
      client_id: document.getElementById("discord-client-id").value.trim(),
      details: document.getElementById("discord-details").value.trim(),
      show_live_status: document.getElementById("discord-live-status").checked,
      state: document.getElementById("discord-state").value.trim(),
      large_image_key: document.getElementById("discord-image-key").value.trim(),
      large_image_text: document.getElementById("discord-image-text").value.trim(),
    };
    await fetch(`${API}/api/config`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ discord_rpc: updated }),
    });
    switchSettingsTab("discord");
  });
}

// ---- Tab: Feedback ----

async function loadFeedbackTab(content) {
  let cfg;
  try {
    cfg = await (await fetch(`${API}/api/config`)).json();
  } catch (e) {
    cfg = { telemetry: {} };
  }
  const telemetryEnabled = cfg.telemetry ? cfg.telemetry.enabled : true;

  content.innerHTML = `
    <label class="toggle-row">
      <span class="toggle-label-text">${t("field_telemetry_enabled")}</span>
      <span class="toggle-switch">
        <input type="checkbox" id="telemetry-enabled" ${telemetryEnabled ? "checked" : ""}>
        <span class="toggle-slider"></span>
      </span>
    </label>
    <p class="settings-hint">${t("telemetry_hint")}</p>
    <div class="settings-divider"></div>
    <p class="settings-hint">${t("feedback_hint")}</p>
    <div class="form-row">
      <label>${t("field_feedback_text")}</label>
      <textarea id="feedback-text" class="notes-area" style="min-height:100px" placeholder="${t("field_feedback_placeholder")}"></textarea>
    </div>
    <div id="feedback-result" class="form-error hidden"></div>
    <div class="form-actions">
      <button class="btn" id="settings-send-feedback-btn">${t("send_feedback")}</button>
    </div>
  `;

  document.getElementById("telemetry-enabled").addEventListener("change", async (e) => {
    const updated = { ...(cfg.telemetry || {}), enabled: e.target.checked };
    await fetch(`${API}/api/config`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ telemetry: updated }),
    });
  });

  document.getElementById("settings-send-feedback-btn").addEventListener("click", async () => {
    const text = document.getElementById("feedback-text").value.trim();
    const resultEl = document.getElementById("feedback-result");
    if (!text) {
      resultEl.textContent = t("feedback_empty");
      resultEl.classList.remove("hidden");
      return;
    }
    const res = await fetch(`${API}/api/telemetry/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    const data = await res.json();
    resultEl.classList.remove("hidden");
    if (data.ok) {
      resultEl.className = "settings-hint";
      resultEl.textContent = t("feedback_sent");
      document.getElementById("feedback-text").value = "";
    } else {
      resultEl.className = "form-error";
      resultEl.textContent = data.error || t("feedback_failed");
    }
  });
}

// ---- Init: Zahnrad-Button + Erstlauf-Check ----

document.getElementById("settings-btn").addEventListener("click", () => openSettings(false));

(async function initOnboardingCheck() {
  await (window.i18nReadyPromise || Promise.resolve());
  try {
    const cfg = await (await fetch(`${API}/api/config`)).json();
    if (!cfg.onboarding_complete) {
      openSettings(true);
    }
  } catch (e) {
    /* still */
  }
})();
