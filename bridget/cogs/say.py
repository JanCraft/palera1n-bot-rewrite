import discord

from typing import Optional
from discord import app_commands

from utils import Cog, send_error, send_success, cfg


class Say(Cog):
    @app_commands.guilds(cfg.guild_id)
    @app_commands.command()
    @app_commands.checks.has_permissions(manage_messages=True)
    async def say(self, ctx: discord.Interaction, message: str, channel: Optional[discord.TextChannel]) -> None:
        """Make the bot say something

        :param message: Message to send
        :param channel: Channel to send to
        """

        channel = channel or ctx.channel
        await channel.send(message)

        await send_success(ctx)

    @say.error
    async def say_error(self, ctx: discord.Interaction, error: Exception) -> None:
        if isinstance(error, app_commands.MissingPermissions):
            await send_error(ctx, "You are not allowed to use this command.")
        else:
            raise error
