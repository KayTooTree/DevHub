"""
cogs/welcome.py — Willkommensnachricht im Welcome-Kanal, sobald jemand
dem Server beitritt. Nutzt den vom Setup-Cog automatisch angelegten
Welcome-Kanal (siehe guild_store.py).
"""

import discord
from discord.ext import commands

import guild_store


class Welcome(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        cfg = guild_store.get_guild(member.guild.id)

        welcome_channel_id = cfg.get("welcome_channel_id")
        if welcome_channel_id:
            channel = self.bot.get_channel(int(welcome_channel_id))
            if channel:
                embed = discord.Embed(
                    description=f"👋 Willkommen auf **{member.guild.name}**, {member.mention}!\n"
                                f"Schau gern im Support-Kanal vorbei, falls du Fragen hast.",
                    color=discord.Color.green(),
                )
                embed.set_thumbnail(url=member.display_avatar.url)
                embed.set_footer(text=f"Mitglied #{member.guild.member_count}")
                try:
                    await channel.send(embed=embed)
                except discord.Forbidden:
                    pass

        log_channel_id = cfg.get("log_channel_id")
        if log_channel_id:
            log_channel = self.bot.get_channel(int(log_channel_id))
            if log_channel:
                embed = discord.Embed(
                    description=f"➡️ {member.mention} ist beigetreten (`{member.id}`)",
                    color=discord.Color.dark_green(),
                    timestamp=discord.utils.utcnow(),
                )
                try:
                    await log_channel.send(embed=embed)
                except discord.Forbidden:
                    pass


async def setup(bot):
    await bot.add_cog(Welcome(bot))
