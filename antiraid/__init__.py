from .antiraid import AntiRaid
from discord.ext import commands


def setup(bot: commands.Bot):
    bot.add_cog(AntiRaid(bot))
