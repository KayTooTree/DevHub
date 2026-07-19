"""
cogs/misc.py — Allgemeine Commands (Ping etc.).
"""

import discord
from discord import app_commands
from discord.ext import commands


class Misc(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ping", description="Zeigt die aktuelle Bot-Latenz.")
    async def ping(self, interaction: discord.Interaction):
        latency_ms = round(self.bot.latency * 1000)
        await interaction.response.send_message(f"🏓 Pong! `{latency_ms}ms`", ephemeral=True)

    @app_commands.command(name="info", description="Infos über den DevHub Bot.")
    async def info(self, interaction: discord.Interaction):
        active = self.bot.telemetry.active_count() if self.bot.telemetry else 0
        embed = discord.Embed(
            title="DevHub Bot",
            description="Moderations- und Community-Bot fürs DevHub Coding Studio.",
            color=discord.Color.blurple(),
        )
        embed.add_field(name="Aktive DevHub-Instanzen", value=str(active), inline=True)
        embed.add_field(name="Server", value=str(len(self.bot.guilds)), inline=True)
        embed.add_field(name="Repo", value="[GitHub](https://github.com/KayTooTree/DevHub.git)", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)


async def setup(bot):
    await bot.add_cog(Misc(bot))
