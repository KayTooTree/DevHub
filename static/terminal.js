/*
 * terminal.js — Voll eingebettetes, interaktives Terminal.
 *
 * xterm.js rendert im Browser eine echte Terminal-Oberflaeche. Ueber eine
 * Socket.IO-Verbindung (Namespace /pty) ist es 1:1 an eine echte Shell
 * (PowerShell auf Windows, bash auf Unix) auf dem lokalen Rechner
 * angebunden. Tastatureingaben gehen direkt an die Shell, deren Output
 * kommt live zurueck — kein Simulations-Terminal, sondern eine reale
 * interaktive Session.
 */

(function () {
  const container = document.getElementById("xterm-container");
  if (!container) return;

  const term = new Terminal({
    fontFamily: "'Share Tech Mono', monospace",
    fontSize: 14,
    convertEol: true,
    theme: {
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
    },
    cursorBlink: true,
    scrollback: 5000,
  });

  const fitAddon = new FitAddon.FitAddon();
  term.loadAddon(fitAddon);
  term.open(container);
  fitAddon.fit();

  const socket = io("/pty", { transports: ["websocket", "polling"] });

  function sendResize() {
    try {
      fitAddon.fit();
      socket.emit("resize", { cols: term.cols, rows: term.rows });
    } catch (e) {
      /* Container evtl. noch nicht sichtbar/layoutet, naechster Resize greift */
    }
  }

  socket.on("connect", () => {
    term.writeln("\x1b[38;2;77;255;136m[DEVHUB] Verbunden. Live-Shell gestartet.\x1b[0m");
    sendResize();
  });

  socket.on("disconnect", () => {
    term.writeln("\r\n\x1b[38;2;255;59;59m[DEVHUB] Verbindung getrennt.\x1b[0m");
  });

  socket.on("pty-output", (data) => {
    term.write(data);
  });

  term.onData((data) => {
    socket.emit("pty-input", data);
  });

  let resizeTimeout;
  window.addEventListener("resize", () => {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(sendResize, 150);
  });

  // Falls das Panel erst spaeter sichtbar wird (z.B. nach Layout-Wechsel)
  new ResizeObserver(() => sendResize()).observe(container);

  window.__devhubTerm = term;
})();
