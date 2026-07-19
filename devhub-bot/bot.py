"""
DEVHUB Bot — Discord-Bot fuers Coding-Studio + Telemetrie-Endpunkt fuer
den DevHub Client.

Ein einziger Prozess:
  - discord.py Bot (Slash-Commands, Moderation, Tickets, Logs, Welcome)
  - eingebauter aiohttp-Webserver (Heartbeat/Feedback vom DevHub Client)

Der Bot-Token verlaesst diesen Prozess nie. Der DevHub Client redet
ausschliesslich mit dem eingebauten Webserver (siehe telemetry_server.py),
nie direkt mit Discord.
"""

import asyncio
import json
import logging
from pathlib import Path

import discord
from discord.ext import commands

from telemetry_server import TelemetryServer

BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "config.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("devhub-bot")


def load_config():
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(
            f"{CONFIG_FILE} fehlt. Siehe README.md fuer die benoetigten Felder."
        )
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


CONFIG = load_config()

intents = discord.Intents.default()
intents.members = True          # fuer Willkommensnachricht + Member-Events
intents.message_content = True  # fuer Message-Logging (Edit/Delete)

bot = commands.Bot(command_prefix="!devhub-", intents=intents, help_command=None)
bot.devhub_config = CONFIG
bot.telemetry = None  # wird in main() gesetzt, sobald der Webserver laeuft

INITIAL_EXTENSIONS = [
    "cogs.misc",
    "cogs.moderation",
    "cogs.welcome",
    "cogs.logging_cog",
    "cogs.setup_cog",
    "cogs.tickets",
    "cogs.verify",
]


@bot.event
async def on_ready():
    log.info(f"Eingeloggt als {bot.user} (ID: {bot.user.id})")
    try:
        synced = await bot.tree.sync()
        log.info(f"{len(synced)} Slash-Commands synchronisiert.")
    except Exception as e:
        log.error(f"Fehler beim Sync der Slash-Commands: {e}")
    await update_presence()


async def update_presence():
    """Wird vom Telemetrie-Server aufgerufen, sobald sich die aktive
    Nutzerzahl aendert -- zeigt NUR dem Bot-Profil, nicht einzelnen Usern,
    'Watching X Users using DevHub'."""
    count = bot.telemetry.active_count() if bot.telemetry else 0
    label = "1 User" if count == 1 else f"{count} Users"
    activity = discord.Activity(type=discord.ActivityType.watching, name=f"{label} using DevHub")
    try:
        await bot.change_presence(activity=activity)
    except Exception as e:
        log.warning(f"Presence-Update fehlgeschlagen: {e}")


async def main():
    async with bot:
        for ext in INITIAL_EXTENSIONS:
            await bot.load_extension(ext)
            log.info(f"Cog geladen: {ext}")

        telemetry = TelemetryServer(bot, CONFIG, update_presence)
        bot.telemetry = telemetry
        await telemetry.start()
        log.info(f"Telemetrie-Server laeuft auf Port {CONFIG.get('telemetry_port', 8090)}")

        await bot.start(CONFIG["bot_token"])


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Bot beendet.")
