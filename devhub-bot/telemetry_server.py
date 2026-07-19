"""
telemetry_server.py — Heartbeat- und Feedback-Endpunkte.

Laeuft im selben Prozess/Event-Loop wie der Discord-Bot (kein separater
Prozess, keine Queue/DB noetig). Der DevHub Client redet ausschliesslich
mit diesem HTTP-Server -- nie direkt mit Discord, nie mit dem Bot-Token.

Heartbeat zaehlt anonyme Client-Instanzen (zufaellige, lokal generierte
instance_id), NICHT einzelne Discord-Nutzer. Die aktive Anzahl wird als
Bot-Presence angezeigt ("Watching X Users using DevHub") -- sichtbar im
Bot-Profil, nicht bei einzelnen Usern.
"""

import asyncio
import hmac
import time

from aiohttp import web

import discord
import verify_store

HEARTBEAT_TIMEOUT_SECONDS = 30
CLEANUP_INTERVAL_SECONDS = 10
MAX_FEEDBACK_LENGTH = 2000


class TelemetryServer:
    def __init__(self, bot, config, on_active_count_changed):
        self.bot = bot
        self.config = config
        self.on_active_count_changed = on_active_count_changed
        self._active = {}  # instance_id -> letzter Heartbeat-Zeitstempel
        self._runner = None
        self._cleanup_task = None

    def active_count(self):
        now = time.time()
        return sum(1 for ts in self._active.values() if now - ts <= HEARTBEAT_TIMEOUT_SECONDS)

    def _check_secret(self, request):
        expected = self.config.get("shared_secret", "")
        if not expected:
            # Kein Secret konfiguriert -- bewusst offen, aber nicht empfohlen.
            # Siehe README: config.json -> shared_secret setzen.
            return True
        provided = request.headers.get("X-DevHub-Secret", "")
        return hmac.compare_digest(provided, expected)

    async def handle_heartbeat(self, request):
        if not self._check_secret(request):
            return web.json_response({"error": "unauthorized"}, status=401)
        try:
            data = await request.json()
        except Exception:
            data = {}

        instance_id = str(data.get("instance_id") or "")[:128]  # laengenbegrenzt
        if not instance_id:
            return web.json_response({"error": "instance_id fehlt"}, status=400)

        was_new = instance_id not in self._active
        self._active[instance_id] = time.time()

        if was_new:
            await self.on_active_count_changed()

        return web.json_response({"ok": True, "active": self.active_count()})

    async def handle_feedback(self, request):
        if not self._check_secret(request):
            return web.json_response({"error": "unauthorized"}, status=401)
        try:
            data = await request.json()
        except Exception:
            data = {}

        text = (data.get("text") or "").strip()
        instance_id = str(data.get("instance_id") or "unbekannt")[:128]
        if not text:
            return web.json_response({"error": "leerer Text"}, status=400)
        text = text[:MAX_FEEDBACK_LENGTH]

        channel_id = self.config.get("feedback_channel_id")
        posted = False
        if channel_id:
            channel = self.bot.get_channel(int(channel_id))
            if channel:
                embed = discord.Embed(
                    title="Neues Feedback",
                    description=text,
                    color=discord.Color.blurple(),
                    timestamp=discord.utils.utcnow(),
                )
                embed.set_footer(text=f"Instanz: {instance_id[:16]}...")
                try:
                    await channel.send(embed=embed)
                    posted = True
                except Exception:
                    posted = False

        return web.json_response({"ok": True, "posted": posted})

    async def handle_health(self, request):
        return web.json_response({"ok": True, "active_users": self.active_count()})

    async def handle_verify_status(self, request):
        if not self._check_secret(request):
            return web.json_response({"error": "unauthorized"}, status=401)
        code = request.query.get("code", "").strip().upper()
        if not code:
            return web.json_response({"error": "code fehlt"}, status=400)
        entry = verify_store.get_claim(code)
        if not entry or not entry.get("claimed"):
            return web.json_response({"claimed": False})
        return web.json_response({
            "claimed": True,
            "discord_id": entry["discord_id"],
            "username": entry["username"],
            "display_name": entry["display_name"],
            "avatar_url": entry["avatar_url"],
            "roles": entry["roles"],
        })

    async def _cleanup_loop(self):
        while True:
            await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
            now = time.time()
            before = len(self._active)
            self._active = {
                k: v for k, v in self._active.items() if now - v <= HEARTBEAT_TIMEOUT_SECONDS
            }
            if len(self._active) != before:
                await self.on_active_count_changed()

    async def start(self):
        app = web.Application()
        app.router.add_post("/heartbeat", self.handle_heartbeat)
        app.router.add_post("/feedback", self.handle_feedback)
        app.router.add_get("/health", self.handle_health)
        app.router.add_get("/verify/status", self.handle_verify_status)

        self._runner = web.AppRunner(app)
        await self._runner.setup()
        port = self.config.get("telemetry_port", 8090)
        site = web.TCPSite(self._runner, "0.0.0.0", port)
        await site.start()

        self._cleanup_task = asyncio.create_task(self._cleanup_loop())

    async def stop(self):
        if self._cleanup_task:
            self._cleanup_task.cancel()
        if self._runner:
            await self._runner.cleanup()
