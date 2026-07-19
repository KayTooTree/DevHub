/*
 * cheatsheet.js — Durchsuchbare Befehlsreferenz. Laedt cheatsheet.json
 * vom Backend; Nutzer koennen diese Datei direkt erweitern (kein
 * Editor-UI noetig, analog zu repos.json vor der Settings-UI).
 */

let cheatsheetData = [];

async function loadCheatsheet() {
  const content = document.getElementById("cheatsheet-content");
  try {
    const res = await fetch(`${API}/api/cheatsheet`);
    cheatsheetData = await res.json();
    renderCheatsheet("");
  } catch (e) {
    content.innerHTML = `<div class="form-error">${t("settings_load_error")}</div>`;
  }
}

function renderCheatsheet(query) {
  const content = document.getElementById("cheatsheet-content");
  const q = query.trim().toLowerCase();

  const filtered = q
    ? cheatsheetData.filter(
        (e) =>
          e.command.toLowerCase().includes(q) ||
          e.description.toLowerCase().includes(q) ||
          e.category.toLowerCase().includes(q)
      )
    : cheatsheetData;

  if (!filtered.length) {
    content.innerHTML = `<div class="settings-hint">${t("cheatsheet_no_results")}</div>`;
    return;
  }

  const byCategory = {};
  filtered.forEach((entry) => {
    byCategory[entry.category] = byCategory[entry.category] || [];
    byCategory[entry.category].push(entry);
  });

  let html = "";
  for (const category of Object.keys(byCategory)) {
    html += `<div class="cheatsheet-category">${escapeHtml(category)}</div>`;
    for (const entry of byCategory[category]) {
      html += `
        <div class="cheatsheet-entry">
          <div class="cheatsheet-cmd-wrap">
            <div class="cheatsheet-cmd">${escapeHtml(entry.command)}</div>
            <div class="cheatsheet-desc">${escapeHtml(entry.description)}</div>
          </div>
          <button class="btn btn-small cheatsheet-copy-btn" data-cmd="${escapeHtml(entry.command)}">${t("dt_copy")}</button>
        </div>
      `;
    }
  }
  content.innerHTML = html;

  content.querySelectorAll(".cheatsheet-copy-btn").forEach((btn) => {
    btn.addEventListener("click", () => copyToClipboard(btn.dataset.cmd, btn));
  });
}

document.getElementById("cheatsheet-search").addEventListener("input", (e) => {
  renderCheatsheet(e.target.value);
});

loadCheatsheet();
