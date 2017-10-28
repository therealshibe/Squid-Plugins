from .bundletest import BundleTest
from redbot.core import data_manager


def setup(bot):
    cog = BundleTest()
    data_manager.load_bundled_data(cog, __file__)
    bot.add_cog(cog)
