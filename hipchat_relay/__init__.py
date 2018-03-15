from .hipchat_relay import HipchatRelay


async def setup(bot):
    cog = HipchatRelay()
    await cog.initialize(bot)
    bot.add_cog(cog)