/*
 * devtools.js — Kleine, aber vollstaendige Sammlung an Dev-Alltagswerkzeugen,
 * komplett clientseitig (kein Backend-Roundtrip noetig). Nach dem Vorbild
 * von Tools wie DevToys: Base64, URL-Encoding, JSON-Formatter,
 * Hash-Generator, UUID-Generator, Timestamp-Konverter, Farbkonverter.
 */

let currentDevTool = "base64";

function copyToClipboard(text, btn) {
  navigator.clipboard.writeText(text).then(() => {
    if (btn) {
      const original = btn.textContent;
      btn.textContent = t("copied");
      setTimeout(() => (btn.textContent = original), 1200);
    }
  });
}

function switchDevTool(tool) {
  currentDevTool = tool;
  document.querySelectorAll("#devtools-tabs .server-panel-tab").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.tool === tool);
  });
  const content = document.getElementById("devtools-content");
  const renderers = {
    base64: renderBase64Tool,
    url: renderUrlTool,
    json: renderJsonTool,
    hash: renderHashTool,
    uuid: renderUuidTool,
    timestamp: renderTimestampTool,
    color: renderColorTool,
  };
  content.innerHTML = "";
  (renderers[tool] || renderBase64Tool)(content);
}

// ---- Base64 ----

function renderBase64Tool(content) {
  content.innerHTML = `
    <div class="form-row">
      <label>${t("dt_input")}</label>
      <textarea id="dt-b64-input" class="notes-area" style="min-height:90px"></textarea>
    </div>
    <div class="form-actions">
      <button class="btn btn-small" id="dt-b64-encode">${t("dt_encode")}</button>
      <button class="btn btn-small" id="dt-b64-decode">${t("dt_decode")}</button>
    </div>
    <div class="form-row">
      <label>${t("dt_output")}</label>
      <textarea id="dt-b64-output" class="notes-area" style="min-height:90px" readonly></textarea>
    </div>
    <div class="form-actions">
      <button class="btn btn-small" id="dt-b64-copy">${t("dt_copy")}</button>
    </div>
  `;
  const input = document.getElementById("dt-b64-input");
  const output = document.getElementById("dt-b64-output");

  document.getElementById("dt-b64-encode").addEventListener("click", () => {
    try {
      output.value = btoa(unescape(encodeURIComponent(input.value)));
    } catch (e) {
      output.value = `${t("dt_error")}: ${e.message}`;
    }
  });
  document.getElementById("dt-b64-decode").addEventListener("click", () => {
    try {
      output.value = decodeURIComponent(escape(atob(input.value.trim())));
    } catch (e) {
      output.value = `${t("dt_error")}: ${t("dt_invalid_base64")}`;
    }
  });
  document.getElementById("dt-b64-copy").addEventListener("click", (e) => copyToClipboard(output.value, e.target));
}

// ---- URL Encode/Decode ----

function renderUrlTool(content) {
  content.innerHTML = `
    <div class="form-row">
      <label>${t("dt_input")}</label>
      <textarea id="dt-url-input" class="notes-area" style="min-height:90px"></textarea>
    </div>
    <div class="form-actions">
      <button class="btn btn-small" id="dt-url-encode">${t("dt_encode")}</button>
      <button class="btn btn-small" id="dt-url-decode">${t("dt_decode")}</button>
    </div>
    <div class="form-row">
      <label>${t("dt_output")}</label>
      <textarea id="dt-url-output" class="notes-area" style="min-height:90px" readonly></textarea>
    </div>
    <div class="form-actions">
      <button class="btn btn-small" id="dt-url-copy">${t("dt_copy")}</button>
    </div>
  `;
  const input = document.getElementById("dt-url-input");
  const output = document.getElementById("dt-url-output");

  document.getElementById("dt-url-encode").addEventListener("click", () => {
    output.value = encodeURIComponent(input.value);
  });
  document.getElementById("dt-url-decode").addEventListener("click", () => {
    try {
      output.value = decodeURIComponent(input.value);
    } catch (e) {
      output.value = `${t("dt_error")}: ${e.message}`;
    }
  });
  document.getElementById("dt-url-copy").addEventListener("click", (e) => copyToClipboard(output.value, e.target));
}

// ---- JSON Formatter ----

function renderJsonTool(content) {
  content.innerHTML = `
    <div class="form-row">
      <label>${t("dt_input")}</label>
      <textarea id="dt-json-input" class="notes-area" style="min-height:140px"></textarea>
    </div>
    <div class="form-actions">
      <button class="btn btn-small" id="dt-json-format">${t("dt_format")}</button>
      <button class="btn btn-small" id="dt-json-minify">${t("dt_minify")}</button>
    </div>
    <div id="dt-json-error" class="form-error hidden"></div>
    <div class="form-row">
      <label>${t("dt_output")}</label>
      <textarea id="dt-json-output" class="notes-area" style="min-height:140px" readonly></textarea>
    </div>
    <div class="form-actions">
      <button class="btn btn-small" id="dt-json-copy">${t("dt_copy")}</button>
    </div>
  `;
  const input = document.getElementById("dt-json-input");
  const output = document.getElementById("dt-json-output");
  const errEl = document.getElementById("dt-json-error");

  function run(indent) {
    errEl.classList.add("hidden");
    try {
      const parsed = JSON.parse(input.value);
      output.value = JSON.stringify(parsed, null, indent);
    } catch (e) {
      errEl.textContent = `${t("dt_invalid_json")}: ${e.message}`;
      errEl.classList.remove("hidden");
      output.value = "";
    }
  }

  document.getElementById("dt-json-format").addEventListener("click", () => run(2));
  document.getElementById("dt-json-minify").addEventListener("click", () => run(0));
  document.getElementById("dt-json-copy").addEventListener("click", (e) => copyToClipboard(output.value, e.target));
}

// ---- Hash Generator ----

async function sha(algo, text) {
  const enc = new TextEncoder().encode(text);
  const buf = await crypto.subtle.digest(algo, enc);
  return Array.from(new Uint8Array(buf)).map((b) => b.toString(16).padStart(2, "0")).join("");
}

function renderHashTool(content) {
  content.innerHTML = `
    <div class="form-row">
      <label>${t("dt_input")}</label>
      <textarea id="dt-hash-input" class="notes-area" style="min-height:90px"></textarea>
    </div>
    <div class="form-actions">
      <button class="btn btn-small" id="dt-hash-run">${t("dt_generate")}</button>
    </div>
    <div class="form-row"><label>SHA-1</label><input id="dt-hash-sha1" class="dt-hash-out" readonly></div>
    <div class="form-row"><label>SHA-256</label><input id="dt-hash-sha256" class="dt-hash-out" readonly></div>
    <div class="form-row"><label>SHA-512</label><input id="dt-hash-sha512" class="dt-hash-out" readonly></div>
    <p class="settings-hint">${t("dt_hash_hint")}</p>
  `;
  document.getElementById("dt-hash-run").addEventListener("click", async () => {
    const text = document.getElementById("dt-hash-input").value;
    document.getElementById("dt-hash-sha1").value = await sha("SHA-1", text);
    document.getElementById("dt-hash-sha256").value = await sha("SHA-256", text);
    document.getElementById("dt-hash-sha512").value = await sha("SHA-512", text);
  });
}

// ---- UUID Generator ----

function renderUuidTool(content) {
  content.innerHTML = `
    <div class="form-row">
      <label>${t("dt_uuid_count")}</label>
      <input id="dt-uuid-count" type="number" value="1" min="1" max="50">
    </div>
    <div class="form-actions">
      <button class="btn btn-small" id="dt-uuid-generate">${t("dt_generate")}</button>
      <button class="btn btn-small" id="dt-uuid-copy-all">${t("dt_copy_all")}</button>
    </div>
    <textarea id="dt-uuid-output" class="notes-area" style="min-height:140px" readonly></textarea>
  `;
  const output = document.getElementById("dt-uuid-output");

  function generate() {
    const count = Math.max(1, Math.min(50, parseInt(document.getElementById("dt-uuid-count").value, 10) || 1));
    const uuids = Array.from({ length: count }, () => crypto.randomUUID());
    output.value = uuids.join("\n");
  }

  document.getElementById("dt-uuid-generate").addEventListener("click", generate);
  document.getElementById("dt-uuid-copy-all").addEventListener("click", (e) => copyToClipboard(output.value, e.target));
  generate();
}

// ---- Timestamp Converter ----

function renderTimestampTool(content) {
  const nowSec = Math.floor(Date.now() / 1000);
  content.innerHTML = `
    <div class="form-row">
      <label>${t("dt_unix_timestamp")}</label>
      <input id="dt-ts-input" type="text" value="${nowSec}">
    </div>
    <div class="form-actions">
      <button class="btn btn-small" id="dt-ts-now">${t("dt_now")}</button>
      <button class="btn btn-small" id="dt-ts-convert">${t("dt_convert")}</button>
    </div>
    <div class="form-row"><label>UTC</label><input id="dt-ts-utc" class="dt-hash-out" readonly></div>
    <div class="form-row"><label>${t("dt_local_time")}</label><input id="dt-ts-local" class="dt-hash-out" readonly></div>
    <div class="form-row"><label>ISO 8601</label><input id="dt-ts-iso" class="dt-hash-out" readonly></div>
    <p class="settings-hint">${t("dt_ts_hint")}</p>
  `;

  function convert() {
    let raw = document.getElementById("dt-ts-input").value.trim();
    let n = Number(raw);
    if (Number.isNaN(n)) return;
    // Heuristik: 13-stellig -> Millisekunden, sonst Sekunden
    const ms = raw.length >= 13 ? n : n * 1000;
    const date = new Date(ms);
    document.getElementById("dt-ts-utc").value = date.toUTCString();
    document.getElementById("dt-ts-local").value = date.toString();
    document.getElementById("dt-ts-iso").value = date.toISOString();
  }

  document.getElementById("dt-ts-now").addEventListener("click", () => {
    document.getElementById("dt-ts-input").value = Math.floor(Date.now() / 1000);
    convert();
  });
  document.getElementById("dt-ts-convert").addEventListener("click", convert);
  convert();
}

// ---- Color Converter ----

function hexToRgb(hex) {
  hex = hex.replace("#", "");
  if (hex.length === 3) hex = hex.split("").map((c) => c + c).join("");
  const num = parseInt(hex, 16);
  return { r: (num >> 16) & 255, g: (num >> 8) & 255, b: num & 255 };
}

function rgbToHsl(r, g, b) {
  r /= 255; g /= 255; b /= 255;
  const max = Math.max(r, g, b), min = Math.min(r, g, b);
  let h, s, l = (max + min) / 2;
  if (max === min) { h = s = 0; }
  else {
    const d = max - min;
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min);
    switch (max) {
      case r: h = (g - b) / d + (g < b ? 6 : 0); break;
      case g: h = (b - r) / d + 2; break;
      default: h = (r - g) / d + 4;
    }
    h /= 6;
  }
  return { h: Math.round(h * 360), s: Math.round(s * 100), l: Math.round(l * 100) };
}

function renderColorTool(content) {
  content.innerHTML = `
    <div class="form-row">
      <label>${t("dt_color_hex")}</label>
      <input id="dt-color-hex" type="text" value="#35f0e8">
    </div>
    <div class="form-actions">
      <button class="btn btn-small" id="dt-color-convert">${t("dt_convert")}</button>
    </div>
    <div id="dt-color-swatch" class="dt-color-swatch"></div>
    <div class="form-row"><label>RGB</label><input id="dt-color-rgb" class="dt-hash-out" readonly></div>
    <div class="form-row"><label>HSL</label><input id="dt-color-hsl" class="dt-hash-out" readonly></div>
  `;

  function convert() {
    const hex = document.getElementById("dt-color-hex").value.trim();
    try {
      const { r, g, b } = hexToRgb(hex);
      const { h, s, l } = rgbToHsl(r, g, b);
      document.getElementById("dt-color-rgb").value = `rgb(${r}, ${g}, ${b})`;
      document.getElementById("dt-color-hsl").value = `hsl(${h}, ${s}%, ${l}%)`;
      document.getElementById("dt-color-swatch").style.background = hex;
    } catch (e) {
      /* ungueltiger Hex-Wert -- Swatch bleibt einfach unveraendert */
    }
  }

  document.getElementById("dt-color-convert").addEventListener("click", convert);
  document.getElementById("dt-color-hex").addEventListener("input", convert);
  convert();
}

// ---- Init ----

document.querySelectorAll("#devtools-tabs .server-panel-tab").forEach((btn) => {
  btn.addEventListener("click", () => switchDevTool(btn.dataset.tool));
});
switchDevTool("base64");
