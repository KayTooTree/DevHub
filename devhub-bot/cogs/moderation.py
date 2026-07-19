"""
cogs/moderation.py — Standard-Moderationswerkzeuge.

Jeder Befehl ist ueber Discords eigenes Berechtigungssystem abgesichert
(@app_commands.default_permissions) -- Server-Owner koennen das ueber
Server-Einstellungen -> Integrationen jederzeit granular anpassen, ganz
ohne eigene Rollen-Logik im Bot.
"""

import datetime

import discord
from discord import app_commands
from discord.ext import commands

import warnings_store
from cogs.logging_cog import log_mod_action


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ------------------------------------------------------------------
    # Warn
    # ------------------------------------------------------------------

    @app_commands.command(name="warn", description="Verwarnt ein Mitglied.")
    @app_commands.describe(member="Das zu verwarnende Mitglied", reason="Grund der Verwarnung")
    @app_commands.default_permissions(moderate_members=True)
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str):
        count = warnings_store.add_warning(interaction.guild_id, member.id, interaction.user.id, reason)
        await interaction.response.send_message(
            f"⚠️ {member.mention} wurde verwarnt. Grund: {reason} (Verwarnung #{count})",
            ephemeral=True,
        )
        try:
            await member.send(f"Du wurdest auf **{interaction.guild.name}** verwarnt.\nGrund: {reason}")
        except discord.Forbidden:
            pass  # DMs geschlossen -- kein Blocker fuer die eigentliche Aktion
        await log_mod_action(
            self.bot, interaction.guild, "WARN", moderator=interaction.user, target=member, reason=reason
        )

    @app_commands.command(name="warnings", description="Zeigt alle Verwarnungen eines Mitglieds.")
    @app_commands.default_permissions(moderate_members=True)
    async def warnings_cmd(self, interaction: discord.Interaction, member: discord.Member):
        entries = warnings_store.get_warnings(interaction.guild_id, member.id)
        if not entries:
            await interaction.response.send_message(f"{member.mention} hat keine Verwarnungen.", ephemeral=True)
            return

        embed = discord.Embed(title=f"Verwarnungen von {member.display_name}", color=discord.Color.orange())
        for i, entry in enumerate(entries[-15:], 1):
            mod = interaction.guild.get_member(int(entry["moderator_id"]))
            mod_name = mod.display_name if mod else "Unbekannt"
            ts_label = f"<t:{int(entry['ts'])}:R>"
            embed.add_field(name=f"#{i} — {ts_label}", value=f"{entry['reason']} (von {mod_name})", inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="clearwarnings", description="Löscht alle Verwarnungen eines Mitglieds.")
    @app_commands.default_permissions(moderate_members=True)
    async def clear_warnings_cmd(self, interaction: discord.Interaction, member: discord.Member):
        count = warnings_store.clear_warnings(interaction.guild_id, member.id)
        await interaction.response.send_message(
            f"🧹 {count} Verwarnung(en) von {member.mention} gelöscht.", ephemeral=True
        )
        await log_mod_action(self.bot, interaction.guild, "CLEAR_WARNINGS", moderator=interaction.user, target=member)

    # ------------------------------------------------------------------
    # Kick
    # ------------------------------------------------------------------

    @app_commands.command(name="kick", description="Kickt ein Mitglied vom Server.")
    @app_commands.describe(member="Das zu kickende Mitglied", reason="Grund")
    @app_commands.default_permissions(kick_members=True)
    async def kick(self, interaction: discord.Interaction, member: discord.Member, reason: str = "Kein Grund angegeben"):
        if member.top_role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message("Du kannst dieses Mitglied nicht kicken (gleiche/höhere Rolle).", ephemeral=True)
            return
        try:
            await member.send(f"Du wurdest von **{interaction.guild.name}** gekickt.\nGrund: {reason}")
        except discord.Forbidden:
            pass
        await member.kick(reason=f"{reason} (durch {interaction.user})")
        await interaction.response.send_message(f"👢 {member.mention} wurde gekickt. Grund: {reason}", ephemeral=True)
        await log_mod_action(self.bot, interaction.guild, "KICK", moderator=interaction.user, target=member, reason=reason)

    # ------------------------------------------------------------------
    # Ban / Unban
    # ------------------------------------------------------------------

    @app_commands.command(name="ban", description="Bannt ein Mitglied vom Server.")
    @app_commands.describe(member="Das zu bannende Mitglied", reason="Grund", delete_days="Nachrichten der letzten X Tage löschen (0-7)")
    @app_commands.default_permissions(ban_members=True)
    async def ban(self, interaction: discord.Interaction, member: discord.Member, reason: str = "Kein Grund angegeben", delete_days: app_commands.Range[int, 0, 7] = 0):
        if member.top_role >= interaction.user.top_role and interaction.user.id != interaction.guild.owner_id:
            await interaction.response.send_message("Du kannst dieses Mitglied nicht bannen (gleiche/höhere Rolle).", ephemeral=True)
            return
        try:
            await member.send(f"Du wurdest von **{interaction.guild.name}** gebannt.\nGrund: {reason}")
        except discord.Forbidden:
            pass
        await member.ban(reason=f"{reason} (durch {interaction.user})", delete_message_days=delete_days)
        await interaction.response.send_message(f"🔨 {member.mention} wurde gebannt. Grund: {reason}", ephemeral=True)
        await log_mod_action(self.bot, interaction.guild, "BAN", moderator=interaction.user, target=member, reason=reason)

    @app_commands.command(name="unban", description="Entbannt einen Nutzer per User-ID.")
    @app_commands.describe(user_id="Discord User-ID des zu entbannenden Nutzers", reason="Grund")
    @app_commands.default_permissions(ban_members=True)
    async def unban(self, interaction: discord.Interaction, user_id: str, reason: str = "Kein Grund angegeben"):
        try:
            user = await self.bot.fetch_user(int(user_id))
        except (ValueError, discord.NotFound):
            await interaction.response.send_message("Ungültige oder unbekannte User-ID.", ephemeral=True)
            return
        try:
            await interaction.guild.unban(user, reason=f"{reason} (durch {interaction.user})")
        except discord.NotFound:
            await interaction.response.send_message("Dieser Nutzer ist nicht gebannt.", ephemeral=True)
            return
        await interaction.response.send_message(f"✅ {user} wurde entbannt. Grund: {reason}", ephemeral=True)
        await log_mod_action(self.bot, interaction.guild, "UNBAN", moderator=interaction.user, target=user, reason=reason)

    # ------------------------------------------------------------------
    # Timeout
    # ------------------------------------------------------------------

    @app_commands.command(name="timeout", description="Versetzt ein Mitglied in Timeout (Minuten).")
    @app_commands.describe(member="Das Mitglied", minutes="Dauer in Minuten (max. 40320 = 28 Tage)", reason="Grund")
    @app_commands.default_permissions(moderate_members=True)
    async def timeout(self, interaction: discord.Interaction, member: discord.Member, minutes: app_commands.Range[int, 1, 40320], reason: str = "Kein Grund angegeben"):
        duration = datetime.timedelta(minutes=minutes)
        await member.timeout(duration, reason=f"{reason} (durch {interaction.user})")
        await interaction.response.send_message(
            f"⏱️ {member.mention} wurde für {minutes} Minute(n) in Timeout versetzt. Grund: {reason}", ephemeral=True
        )
        await log_mod_action(self.bot, interaction.guild, "TIMEOUT", moderator=interaction.user, target=member, reason=f"{reason} ({minutes} min)")

    @app_commands.command(name="untimeout", description="Beendet den Timeout eines Mitglieds vorzeitig.")
    @app_commands.default_permissions(moderate_members=True)
    async def untimeout(self, interaction: discord.Interaction, member: discord.Member):
        await member.timeout(None)
        await interaction.response.send_message(f"✅ Timeout von {member.mention} wurde beendet.", ephemeral=True)
        await log_mod_action(self.bot, interaction.guild, "UNTIMEOUT", moderator=interaction.user, target=member)


async def setup(bot):
    await bot.add_cog(Moderation(bot))
