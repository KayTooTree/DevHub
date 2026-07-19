"""
cogs/verify.py — /verify <code>: verknuepft einen DevHub Client mit der
Discord-Identitaet des Nutzers (User-ID, Username, Anzeigename, Avatar,
Rollen). Der Client zeigt vorher einen zufaelligen Code an, siehe
verify_store.py fuer den Ablauf.
"""

import re

import discord
from discord import app_commands
from discord.ext import commands

import verify_store

CODE_PATTERN = re.compile(r"^[A-Z0-9]{6,10}$")


class Verify(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="verify", description="Verknüpft deinen DevHub Client mit deinem Discord-Account.")
    @app_commands.describe(code="Der Code, den dir DevHub angezeigt hat")
    async def verify(self, interaction: discord.Interaction, code: str):
        code = code.strip().upper()
        if not CODE_PATTERN.match(code):
            await interaction.response.send_message(
                "Das sieht nicht nach einem gültigen DevHub-Code aus. Kopier ihn 1:1 aus dem DevHub-Fenster.",
                ephemeral=True,
            )
            return

        roles = []
        member = interaction.user if isinstance(interaction.user, discord.Member) else None
        if member:
            roles = [r.name for r in member.roles if r.name != "@everyone"]

        avatar_url = str(interaction.user.display_avatar.url)
        display_name = member.display_name if member else interaction.user.name

        ok = verify_store.register_claim(
            code=code,
            discord_id=interaction.user.id,
            username=str(interaction.user),
            display_name=display_name,
            avatar_url=avatar_url,
            roles=roles,
        )

        if ok:
            await interaction.response.send_message(
                "✅ Verknüpft! Du kannst jetzt zu DevHub zurückwechseln.", ephemeral=True
            )
        else:
            await interaction.response.send_message(
                "Dieser Code wurde bereits verwendet oder ist abgelaufen. Generier in DevHub einen neuen.",
                ephemeral=True,
            )


async def setup(bot):
    await bot.add_cog(Verify(bot))
