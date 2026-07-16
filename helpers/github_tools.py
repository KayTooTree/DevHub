"""
github_tools.py — Holt oeffentliche Repo-Statistiken (Sterne, offene Issues,
Forks) von der GitHub-API. Nutzt bewusst KEINEN Token, sondern die
unauthentifizierte oeffentliche API (Limit: 60 Anfragen/Stunde/IP) — dafuer
gibt es einen TTL-Cache, damit haeufiges Dashboard-Polling dieses Limit
nicht ausreizt.
"""

import time

try:
    import requests
except ImportError:
    requests = None

_cache = {}
CACHE_TTL_SECONDS = 300  # 5 Minuten


def get_repo_stats(slug):
    """slug im Format 'owner/repo'. Gibt gecachte Werte zurueck, falls
    innerhalb der letzten CACHE_TTL_SECONDS bereits abgefragt."""
    if not slug or requests is None:
        return {"error": "nicht verfuegbar"}

    now = time.time()
    cached = _cache.get(slug)
    if cached and (now - cached["ts"]) < CACHE_TTL_SECONDS:
        return cached["data"]

    try:
        r = requests.get(
            f"https://api.github.com/repos/{slug}",
            timeout=4,
            headers={"Accept": "application/vnd.github+json"},
        )
        if r.status_code == 200:
            data = r.json()
            result = {
                "stars": data.get("stargazers_count"),
                "open_issues": data.get("open_issues_count"),
                "forks": data.get("forks_count"),
            }
        elif r.status_code == 403:
            result = {"error": "API Rate-Limit erreicht"}
        elif r.status_code == 404:
            result = {"error": "Repo nicht gefunden (privat oder falscher Slug?)"}
        else:
            result = {"error": f"HTTP {r.status_code}"}
    except Exception as e:
        result = {"error": str(e)}

    _cache[slug] = {"ts": now, "data": result}
    return result
