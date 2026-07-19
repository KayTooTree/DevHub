"""
cogs/tickets.py — Ticket-System.

Ein Panel mit "Ticket erstellen"-Button im Support-Kanal (wird vom
Setup-Cog automatisch gepostet). Klick erstellt einen privaten Kanal in
der Ticket-Kategorie, sichtbar fuer Opener + Moderator-Rolle + Bot.

Persistente Views (custom_id-basiert) ueberleben Bot-Neustarts -- die
Buttons funktionieren auch nach einem Restart weiter, ohne dass das Panel
neu gepostet werden muss.
"""

import asyncio

import discord
from discord.ext import commands

import guild_store

TICKET_CREATE_CUSTOM_ID = "devhub_ticket_create"
TICKET_CLOSE_CUSTOM_ID = "devhub_ticket_close"


class TicketPanelView(discord.ui.View):
    """Der Button im Support-Kanal. timeout=None + feste custom_id => persistent."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎫 Ticket erstellen", style=discord.ButtonStyle.primary, custom_id=TICKET_CREATE_CUSTOM_ID)
    async def create_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        cfg = guild_store.get_guild(guild.id)

        category_id = cfg.get("ticket_category_id")
        category = guild.get_channel(int(category_id)) if category_id else None
        if not category:
            await interaction.response.send_message(
                "Ticket-Kategorie nicht gefunden — bitte `/setup` erneut ausführen.", ephemeral=True
            )
            return

        # Bereits offenes Ticket? (Opener-ID steht im Kanal-Topic)
        existing = discord.utils.find(
            lambda c: c.topic == str(interaction.user.id), category.text_channels
        )
        if existing:
            await interaction.response.send_message(
                f"Du hast bereits ein offenes Ticket: {existing.mention}", ephemeral=True
            )
            return

        mod_role = guild.get_role(int(cfg["moderator_role_id"])) if cfg.get("moderator_role_id") else None

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True),
        }
        if mod_role:
            overwrites[mod_role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        safe_name = "".join(c for c in interaction.user.name.lower() if c.isalnum() or c == "-")[:20] or "user"
        channel = await guild.create_text_channel(
            f"ticket-{safe_name}",
            category=category,
            overwrites=overwrites,
            topic=str(interaction.user.id),
            reason=f"Ticket erstellt von {interaction.user}",
        )

        embed = discord.Embed(
            title="🎫 Neues Ticket",
            description=f"Hallo {interaction.user.mention}, beschreib dein Anliegen — ein Teammitglied meldet sich.",
            color=discord.Color.blurple(),
        )
        await channel.send(embed=embed, view=TicketCloseView())
        await interaction.response.send_message(f"Ticket erstellt: {channel.mention}", ephemeral=True)


class TicketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔒 Ticket schließen", style=discord.ButtonStyle.danger, custom_id=TICKET_CLOSE_CUSTOM_ID)
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Ticket wird in 5 Sekunden geschlossen...")
        await asyncio.sleep(5)
        try:
            await interaction.channel.delete(reason=f"Ticket geschlossen von {interaction.user}")
        except discord.NotFound:
            pass


async def post_ticket_panel(channel: discord.TextChannel):
    embed = discord.Embed(
        title="Support",
        description="Brauchst du Hilfe? Klick unten, um ein privates Ticket zu öffnen.",
        color=discord.Color.blurple(),
    )
    await channel.send(embed=embed, view=TicketPanelView())


class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


async def setup(bot):
    # Persistente Views einmalig registrieren, damit die Buttons auch nach
    # einem Bot-Neustart weiterhin funktionieren (Discord ruft ueber die
    # custom_id zurueck, unabhaengig davon, welche Nachricht das war).
    bot.add_view(TicketPanelView())
    bot.add_view(TicketCloseView())
    await bot.add_cog(Tickets(bot))
