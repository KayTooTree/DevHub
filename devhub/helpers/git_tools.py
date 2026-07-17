"""
git_tools.py — Alles rund um die ueberwachten Git-Repositories.

check_repo_status() macht bewusst nur ein "git fetch" (liest Remote-Refs),
niemals automatisch einen Merge/Pull — das bleibt eine explizite
Nutzer-Aktion ueber den Pull-Button im Dashboard.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

IS_WINDOWS = sys.platform == "win32"


def run_git(args, cwd, timeout=15):
    """Fuehrt einen git-Befehl aus und gibt (returncode, stdout, stderr) zurueck."""
    if not Path(cwd).exists():
        return -1, "", f"Arbeitsverzeichnis existiert nicht: {cwd}"
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW if IS_WINDOWS else 0,
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except FileNotFoundError:
        return -1, "", "git nicht gefunden (ist Git installiert und im PATH?)"
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"
    except Exception as e:
        return -1, "", str(e)


def load_repos(repos_file: Path):
    if not repos_file.exists():
        return []
    try:
        with open(repos_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_repos(repos_file: Path, repos):
    with open(repos_file, "w", encoding="utf-8") as f:
        json.dump(repos, f, indent=2, ensure_ascii=False)


def check_repo_status(path):
    p = Path(path)
    if not path or not p.exists():
        return {"status": "MISSING", "detail": "Pfad existiert nicht"}
    if not (p / ".git").exists():
        return {"status": "NOT_A_REPO", "detail": "Kein .git Ordner gefunden"}

    # Remote-Refs aktualisieren, ohne lokale Branches zu veraendern
    code, _, err = run_git(["fetch", "--quiet"], cwd=str(p))
    if code != 0:
        return {"status": "ERROR", "detail": err or "git fetch fehlgeschlagen"}

    _, branch, _ = run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=str(p))
    _, last_commit, _ = run_git(["log", "-1", "--pretty=%h %s"], cwd=str(p))
    _, dirty_out, _ = run_git(["status", "--porcelain"], cwd=str(p))
    dirty_count = len([line for line in dirty_out.splitlines() if line.strip()])

    code, upstream, err = run_git(
        ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"], cwd=str(p)
    )
    if code != 0:
        return {
            "status": "NO_UPSTREAM",
            "detail": "Kein Upstream-Branch konfiguriert",
            "branch": branch,
            "last_commit": last_commit,
            "dirty": dirty_count,
        }

    _, behind, _ = run_git(["rev-list", "--count", "HEAD..@{u}"], cwd=str(p))
    _, ahead, _ = run_git(["rev-list", "--count", "@{u}..HEAD"], cwd=str(p))
    behind = int(behind) if behind.isdigit() else 0
    ahead = int(ahead) if ahead.isdigit() else 0

    if behind == 0 and ahead == 0:
        status = "UP_TO_DATE"
    elif behind > 0 and ahead == 0:
        status = "BEHIND"
    elif behind == 0 and ahead > 0:
        status = "AHEAD"
    else:
        status = "DIVERGED"

    return {
        "status": status,
        "behind": behind,
        "ahead": ahead,
        "upstream": upstream,
        "branch": branch,
        "last_commit": last_commit,
        "dirty": dirty_count,
    }


def pull(path, timeout=60):
    code, out, err = run_git(["pull"], cwd=path, timeout=timeout)
    return {"ok": code == 0, "output": out, "error": err}


def open_in_tool(path, tool):
    """Oeffnet einen Repo-Pfad in VS Code oder im Datei-Explorer des Systems."""
    try:
        if tool == "code":
            subprocess.Popen(["code", path], shell=IS_WINDOWS)
        elif tool == "explorer":
            if IS_WINDOWS:
                subprocess.Popen(["explorer.exe", path])
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        else:
            return {"ok": False, "error": f"unbekanntes tool '{tool}'"}
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}
