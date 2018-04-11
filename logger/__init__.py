from .logger import Logger


async def setup(bot):
    cog = Logger(bot)
    await cog.refresh_levels()
    bot.add_cog(cog)