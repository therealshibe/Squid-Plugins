from discord.ext import commands


class BundleTest:
    @commands.command()
    async def bundled(self, ctx):
        await ctx.send("Yep, I got loaded.")
