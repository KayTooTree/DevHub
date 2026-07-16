/*
 * terminal.js — Voll eingebettetes, interaktives Terminal mit mehreren Tabs.
 *
 * Jeder Tab ist eine komplett eigenstaendige xterm.js-Instanz mit eigener
 * Socket.IO-Verbindung (forceNew: true) -> jede Verbindung bekommt auf dem
 * Server eine eigene echte Shell-Session (siehe pty_bridge.py). Tabs laufen
 * auch im Hintergrund weiter, wenn man zu einem anderen Tab wechselt.
 *
 * WICHTIG: Der Container jedes Terminals braucht "position: relative"
 * (siehe style.css .xterm-pane) — ohne das positioniert xterm.js sein
 * unsichtbares Eingabe-Textfeld falsch, und man kann nicht hineintippen.
 */

(function () {
  const tabsBar = document.getElementById("term-tabs");
  const addBtn = document.getElementById("term-add-btn");
  const panesContainer = document.getElementById("term-panes");
  if (!tabsBar || !panesContainer || !addBtn) return;

  let tabCounter = 0;
  const tabs = [];
  let activeId = null;

  function xtermTheme() {
    return {
      background: "#00000000",
      foreground: "#b9f4ef",
      cursor: "#35f0e8",
      cursorAccent: "#04100f",
      selectionBackground: "rgba(53,240,232,0.3)",
      black: "#04100f",
      brightBlack: "#14625e",
      green: "#4dff88",
      brightGreen: "#4dff88",
      yellow: "#ffb000",
      brightYellow: "#ffb000",
      red: "#ff3b3b",
      brightRed: "#ff3b3b",
      cyan: "#35f0e8",
      brightCyan: "#35f0e8",
      white: "#b9f4ef",
      brightWhite: "#e9fffd",
    };
  }

  function createTab() {
    tabCounter += 1;
    const id = "term-" + tabCounter;

    const tabEl = document.createElement("button");
    tabEl.className = "term-tab";
    tabEl.dataset.id = id;
    tabEl.innerHTML = `<span class="term-tab-label">SHELL ${tabCounter}</span><span class="term-tab-close">×</span>`;
    tabEl.addEventListener("click", (e) => {
      if (e.target.classList.contains("term-tab-close")) return;
      activateTab(id);
    });
    tabEl.querySelector(".term-tab-close").addEventListener("click", (e) => {
      e.stopPropagation();
      closeTab(id);
    });
    tabsBar.insertBefore(tabEl, addBtn);

    const paneEl = document.createElement("div");
    paneEl.className = "xterm-pane";
    paneEl.dataset.id = id;
    panesContainer.appendChild(paneEl);

    let term, fitAddon, socket;
    try {
      term = new Terminal({
        fontFamily: "'Share Tech Mono', monospace",
        fontSize: 14,
        convertEol: true,
        theme: xtermTheme(),
        cursorBlink: true,
        scrollback: 5000,
      });
      fitAddon = new FitAddon.FitAddon();
      term.loadAddon(fitAddon);
      term.open(paneEl);

      socket = io("/pty", { forceNew: true, transports: ["websocket", "polling"] });
    } catch (err) {
      paneEl.innerHTML =
        '<div class="term-error">Terminal konnte nicht geladen werden (xterm.js/Socket.IO nicht erreichbar). ' +
        "Pruefe die Internetverbindung fuer die CDN-Skripte oder nutze den Button 'Externes Fenster'.</div>";
      return null;
    }

    function sendResize() {
      try {
        fitAddon.fit();
        socket.emit("resize", { cols: term.cols, rows: term.rows });
      } catch (e) {
        /* Pane evtl. gerade nicht sichtbar, naechster Versuch klappt */
      }
    }

    socket.on("connect", () => {
      term.writeln("\x1b[38;2;77;255;136m[DEVHUB] Verbunden. Live-Shell gestartet.\x1b[0m");
      sendResize();
    });
    socket.on("disconnect", () => {
      term.writeln("\r\n\x1b[38;2;255;59;59m[DEVHUB] Verbindung getrennt.\x1b[0m");
    });
    socket.on("pty-output", (data) => term.write(data));
    term.onData((data) => socket.emit("pty-input", data));

    // Klick irgendwo in die Pane fokussiert das Terminal-Eingabefeld
    paneEl.addEventListener("mousedown", () => term.focus());

    new ResizeObserver(() => {
      if (activeId === id) sendResize();
    }).observe(paneEl);

    const entry = { id, term, socket, fitAddon, tabEl, paneEl, sendResize };
    tabs.push(entry);
    activateTab(id);
    return entry;
  }

  function activateTab(id) {
    activeId = id;
    tabs.forEach((tb) => {
      const active = tb.id === id;
      tb.tabEl.classList.toggle("active", active);
      tb.paneEl.classList.toggle("active", active);
    });
    const current = tabs.find((tb) => tb.id === id);
    if (current) {
      setTimeout(() => {
        current.sendResize();
        current.term.focus();
      }, 30);
    }
  }

  function closeTab(id) {
    const idx = tabs.findIndex((tb) => tb.id === id);
    if (idx === -1) return;
    const tb = tabs[idx];
    try {
      tb.socket.disconnect();
      tb.term.dispose();
    } catch (e) {
      /* egal, wird sowieso entfernt */
    }
    tb.tabEl.remove();
    tb.paneEl.remove();
    tabs.splice(idx, 1);

    if (tabs.length === 0) {
      createTab();
    } else if (activeId === id) {
      const fallback = tabs[Math.max(0, idx - 1)];
      activateTab(fallback.id);
    }
  }

  addBtn.addEventListener("click", () => createTab());

  window.addEventListener("resize", () => {
    const active = tabs.find((tb) => tb.id === activeId);
    if (active) active.sendResize();
  });

  createTab(); // erster Tab beim Laden der Seite
})();
