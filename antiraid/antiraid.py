import discord
from typing import Callable
from discord.ext import commands

from core import Config

from .buckets import BucketManager, JoinBucket

"""
    Written solely for V3 and the DPY rewrite.
"""


def is_enabled(f: Callable) -> Callable:
    """
    Decorator that checks to see if AntiRaid is enabled.
    :param f: function
    :return: 
    """
    def pred(self, obj, *args, **kwargs):
        """
        :param self:
        :param obj: Must have a `guild` attribute.
        :param args: 
        :param kwargs: 
        :return: 
        """
        try:
            guild = obj.guild
        except AttributeError:
            return

        enabled = self._config.guild(guild).enabled()
        if enabled:
            return f(self, obj, *args, **kwargs)
    return pred


class AntiRaid:

    SETTINGS_PATH = 'data/antiraid/settings.json'

    default_settings = {
        'enabled': False,
        'joins': 5,
        'join_seconds': 30,
        'join_raid_time': 300,
        'posts': 10,
        'post_seconds': 10,
        'post_raid_time': 300,
        'pre_raid_inclusion_time': 60,
        'role': 'AntiRaidMute',
        'channel': None,
        'is_under_raid': False,
        'raid_start_time': 0
    }

    def __init__(self, bot: commands.Bot):
        self._bot = bot

        self._config = Config.get_conf(self.__class__.__name__, 8927347832478324)

        self._config.register_guild(**self.default_settings)

        self._join_bucket_manager = BucketManager(bucket_type=JoinBucket)
        self._member_bucket_manager = BucketManager()

    def _enable(self, ctx: commands.Context, enable: bool=True):
        self._config.guild(ctx.guild).set("enabled", enable)

    def _get_join_bucket_args(self, guild: discord.Guild) -> list:
        guild_settings = self._config.guild(guild)
        return [
            guild,
            guild_settings.joins(),
            1 / guild_settings.join_seconds()
        ]

    def _get_message_bucket_args(self, guild: discord.Guild) -> list:
        guild_settings = self._config.guild(guild)
        return [
            guild_settings.posts(),
            1 / guild_settings.post_seconds()
        ]

    def is_under_raid(self, guild: discord.Guild) -> bool:
        return self._config.guild(guild).is_under_raid()

    @is_enabled
    def consume_join(self, member: discord.Member):
        try:
            bucket = self._join_bucket_manager(member.guild)
        except KeyError:
            args = self._get_join_bucket_args(member.guild)
            bucket = self._join_bucket_manager.add_guild(
                member.guild,
                bucket_args=args
            )
        bucket.consume_join(member.guild)

    @is_enabled
    def consume_message(self, message: discord.Message):
        try:
            bucket = self._member_bucket_manager(message.author)
        except KeyError:
            args = self._get_message_bucket_args(message.guild)
            bucket = self._member_bucket_manager.add_member(
                message.author,
                bucket_args=args
            )
        bucket.consume()

    #region Discord Commands

    @commands.group()
    async def antiraidset(self, ctx):
        pass

    @antiraidset.command()
    async def enable(self, ctx):
        """
        Enables AntiRaid settings on this server.
        """
        self._enable(ctx)

        await ctx.send("AntiRaid enabled.")

    @antiraidset.command()
    async def disable(self, ctx):
        """
        Disables AntiRaid settings on this server.
        """
        self._enable(ctx, False)

        await ctx.send("AntiRaid disabled.")

    #endregion

    #region Event Handlers

    async def on_member_join(self, member: discord.Member):
        self.consume_join(member)

    async def on_message(self, message: discord.Message):
        self.consume_message(message)

    #endregion
