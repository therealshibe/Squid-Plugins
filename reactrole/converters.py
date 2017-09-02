from discord.ext import commands
from discord.ext.commands import Converter


class RegisteredMessage(Converter):
    async def convert(self, ctx, argument) -> int:
        reactrole = ctx.bot.get_cog("ReactRole")
        if reactrole is None:
            raise commands.CommandError("ReactRole not loaded.")

        try:
            message_id = int(argument)
        except ValueError as e:
            raise commands.CommandError("Provided argument was not an integer.") from e

        if not (await reactrole.is_registered(message_id)):
            raise commands.CommandError("Provided integer is not a registered message ID.")

        return message_id
