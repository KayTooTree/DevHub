"""
cogs/logging_cog.py — Zentrales Server-Log: Mod-Aktionen, Message-Edits/
Deletes, Member-Join/Leave. Alles landet im per Setup angelegten Log-Kanal.

log_mod_action() wird von cogs/moderation.py importiert und aufgerufen --
zentrale Stelle, damit das Log-Format an einem Ort gepflegt wird.
"""

import discord
from discord.ext import commands

import guild_store


async def _get_log_channel(bot, guild):
    cfg = guild_store.get_guild(guild.id)
    channel_id = cfg.get("log_channel_id")
    if not channel_id:
        return None
    return bot.get_channel(int(channel_id))


async def log_mod_action(bot, guild, action, moderator, target, reason=None):
    channel = await _get_log_channel(bot, guild)
    if not channel:
        return
    embed = discord.Embed(
        title=f"Mod-Aktion: {action}",
        color=discord.Color.red(),
        timestamp=discord.utils.utcnow(),
    )
    embed.add_field(name="Ziel", value=f"{target} (`{target.id}`)", inline=True)
    embed.add_field(name="Moderator", value=f"{moderator} (`{moderator.id}`)", inline=True)
    if reason:
        embed.add_field(name="Grund", value=reason, inline=False)
    try:
        await channel.send(embed=embed)
    except discord.Forbidden:
        pass


class LoggingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        channel = await _get_log_channel(self.bot, message.guild)
        if not channel:
            return
        embed = discord.Embed(
            title="Nachricht gelöscht",
            description=message.content or "*(kein Textinhalt, z.B. nur Anhang/Embed)*",
            color=discord.Color.dark_orange(),
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(name="Autor", value=f"{message.author} (`{message.author.id}`)", inline=True)
        embed.add_field(name="Kanal", value=message.channel.mention, inline=True)
        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            pass

    @commands.Cog.listener()
    async def on_message_edit(self, before: discord.Message, after: discord.Message):
        if before.author.bot or not before.guild or before.content == after.content:
            return
        channel = await _get_log_channel(self.bot, before.guild)
        if not channel:
            return
        embed = discord.Embed(title="Nachricht bearbeitet", color=discord.Color.gold(), timestamp=discord.utils.utcnow())
        embed.add_field(name="Autor", value=f"{before.author} (`{before.author.id}`)", inline=True)
        embed.add_field(name="Kanal", value=before.channel.mention, inline=True)
        embed.add_field(name="Vorher", value=(before.content or "*leer*")[:1000], inline=False)
        embed.add_field(name="Nachher", value=(after.content or "*leer*")[:1000], inline=False)
        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            pass

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        channel = await _get_log_channel(self.bot, member.guild)
        if not channel:
            return
        embed = discord.Embed(
            description=f"⬅️ {member.mention} hat den Server verlassen (`{member.id}`)",
            color=discord.Color.dark_grey(),
            timestamp=discord.utils.utcnow(),
        )
        try:
            await channel.send(embed=embed)
        except discord.Forbidden:
            pass


async def setup(bot):
    await bot.add_cog(LoggingCog(bot))
