"""
cogs/setup_cog.py — Richtet einen (leeren) Server automatisch ein, sobald
der Bot beitritt: Kategorie mit Welcome/Support/Mod-Logs-Kanaelen, eine
Ticket-Kategorie, eine Moderator-Rolle, und postet das Ticket-Panel.

Idempotent: wird /setup erneut ausgefuehrt (oder war der Bot schon vorher
im Server), werden nur fehlende Teile ergaenzt, nichts doppelt angelegt.
"""

import discord
from discord import app_commands
from discord.ext import commands

import guild_store
from cogs.tickets import post_ticket_panel

CATEGORY_NAME = "DEVHUB STUDIO"
TICKET_CATEGORY_NAME = "TICKETS"
MODERATOR_ROLE_NAME = "Moderator"


async def run_guild_setup(bot, guild: discord.Guild) -> str:
    """Fuehrt das Setup aus (idempotent) und gibt einen Zusammenfassungstext zurueck."""
    cfg = guild_store.get_guild(guild.id)
    created = []

    # ---- Moderator-Rolle ----
    mod_role = guild.get_role(int(cfg["moderator_role_id"])) if cfg.get("moderator_role_id") else None
    if not mod_role:
        mod_role = discord.utils.get(guild.roles, name=MODERATOR_ROLE_NAME)
    if not mod_role:
        mod_role = await guild.create_role(
            name=MODERATOR_ROLE_NAME,
            permissions=discord.Permissions(
                kick_members=True, ban_members=True, moderate_members=True, manage_messages=True
            ),
            reason="DevHub Bot Auto-Setup",
        )
        created.append(f"Rolle {mod_role.mention}")
    guild_store.set_guild(guild.id, moderator_role_id=mod_role.id)

    # ---- Hauptkategorie ----
    category = guild.get_channel(int(cfg["category_id"])) if cfg.get("category_id") else None
    if not category:
        category = discord.utils.get(guild.categories, name=CATEGORY_NAME)
    if not category:
        category = await guild.create_category(CATEGORY_NAME, reason="DevHub Bot Auto-Setup")
        created.append(f"Kategorie **{CATEGORY_NAME}**")
    guild_store.set_guild(guild.id, category_id=category.id)

    # ---- Welcome-Kanal ----
    welcome_channel = guild.get_channel(int(cfg["welcome_channel_id"])) if cfg.get("welcome_channel_id") else None
    if not welcome_channel:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(send_messages=False, view_channel=True),
            guild.me: discord.PermissionOverwrite(send_messages=True, view_channel=True),
        }
        welcome_channel = await guild.create_text_channel(
            "welcome", category=category, overwrites=overwrites, reason="DevHub Bot Auto-Setup"
        )
        created.append(welcome_channel.mention)
    guild_store.set_guild(guild.id, welcome_channel_id=welcome_channel.id)

    # ---- Support-Kanal (Ticket-Panel) ----
    support_channel = guild.get_channel(int(cfg["support_channel_id"])) if cfg.get("support_channel_id") else None
    if not support_channel:
        support_channel = await guild.create_text_channel(
            "support", category=category, reason="DevHub Bot Auto-Setup"
        )
        created.append(support_channel.mention)
        await post_ticket_panel(support_channel)
    guild_store.set_guild(guild.id, support_channel_id=support_channel.id)

    # ---- Mod-Log-Kanal (nur fuer Moderatoren sichtbar) ----
    log_channel = guild.get_channel(int(cfg["log_channel_id"])) if cfg.get("log_channel_id") else None
    if not log_channel:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            mod_role: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }
        log_channel = await guild.create_text_channel(
            "mod-logs", category=category, overwrites=overwrites, reason="DevHub Bot Auto-Setup"
        )
        created.append(log_channel.mention)
    guild_store.set_guild(guild.id, log_channel_id=log_channel.id)

    # ---- Ticket-Kategorie (privat, Ticket-Kanaele werden dynamisch erstellt) ----
    ticket_category = guild.get_channel(int(cfg["ticket_category_id"])) if cfg.get("ticket_category_id") else None
    if not ticket_category:
        ticket_category = discord.utils.get(guild.categories, name=TICKET_CATEGORY_NAME)
    if not ticket_category:
        overwrites = {guild.default_role: discord.PermissionOverwrite(view_channel=False)}
        ticket_category = await guild.create_category(
            TICKET_CATEGORY_NAME, overwrites=overwrites, reason="DevHub Bot Auto-Setup"
        )
        created.append(f"Kategorie **{TICKET_CATEGORY_NAME}**")
    guild_store.set_guild(guild.id, ticket_category_id=ticket_category.id)

    if created:
        summary = "**DevHub Bot Setup abgeschlossen.** Neu angelegt:\n" + "\n".join(f"• {c}" for c in created)
        summary += f"\n\nWeis dein Team die Rolle {mod_role.mention} zu, damit sie Zugriff auf {log_channel.mention} haben und Moderationsbefehle nutzen können."
    else:
        summary = "Setup bereits vollständig — nichts Neues angelegt."

    try:
        await welcome_channel.send(summary)
    except discord.Forbidden:
        pass

    return summary


class SetupCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        try:
            await run_guild_setup(self.bot, guild)
        except discord.Forbidden:
            # Bot hat keine ausreichenden Rechte (z.B. "Rollen verwalten" nicht erteilt)
            pass

    @app_commands.command(name="setup", description="Richtet DevHub Bot Kanäle/Rollen auf diesem Server (erneut) ein.")
    @app_commands.default_permissions(administrator=True)
    async def setup_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        summary = await run_guild_setup(self.bot, interaction.guild)
        await interaction.followup.send(summary, ephemeral=True)


async def setup(bot):
    await bot.add_cog(SetupCog(bot))
