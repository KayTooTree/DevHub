/*
 * boot.js — Kurze "Systemhochfahren"-Animation im Stil eines Command-Centers.
 * Rein kosmetisch, blockiert nichts: das Dashboard laedt im Hintergrund
 * parallel weiter, der Boot-Screen legt sich nur solange als Overlay drueber.
 */

(function () {
  const screen = document.getElementById("boot-screen");
  const linesEl = document.getElementById("boot-lines");
  const barFill = document.getElementById("boot-bar-fill");
  const skipBtn = document.getElementById("boot-skip");
  if (!screen) return;

  const messages = [
    "INITIALIZING KERNEL MODULES...",
    "MOUNTING NETWORK INTERFACES...",
    "ESTABLISHING LOCAL BACKEND LINK...",
    "SCANNING GIT REPOSITORIES...",
    "SPAWNING TERMINAL BRIDGE...",
    "LOADING OPERATOR PROFILE...",
    "ALL SYSTEMS NOMINAL.",
  ];

  let i = 0;
  let done = false;

  function nextLine() {
    if (done) return;
    if (i < messages.length) {
      const line = document.createElement("div");
      line.className = "boot-line";
      line.textContent = "> " + messages[i];
      linesEl.appendChild(line);
      linesEl.scrollTop = linesEl.scrollHeight;
      i += 1;
      barFill.style.width = Math.round((i / messages.length) * 100) + "%";
      setTimeout(nextLine, 220 + Math.random() * 160);
    } else {
      setTimeout(hideBoot, 450);
    }
  }

  function hideBoot() {
    if (done) return;
    done = true;
    screen.classList.add("boot-hidden");
    setTimeout(() => {
      screen.style.display = "none";
    }, 650);
  }

  skipBtn.addEventListener("click", hideBoot);
  nextLine();

  // Sicherheitsnetz: Boot-Screen spaetestens nach 6s ausblenden, egal was ist
  setTimeout(hideBoot, 6000);
})();
