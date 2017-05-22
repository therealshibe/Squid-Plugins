import discord
import time
from typing import Callable
from discord.ext import commands

from core import Config


import os

"""
    Written solely for V3 and the DPY rewrite.
"""


class TokenBucket:
    def __init__(self, bucket_size: int, fill_rate: float):
        """
        TokenBucket initializer
        :param bucket_size: Must be greater than zero
        :param fill_rate: Must be greater than zero
        """
        self.tokens = 0

        self.max_size = int(bucket_size)
        if self.max_size <= 0:
            raise ValueError("Bucket size must be greater than 0.")

        if fill_rate > 1:
            fill_rate = 1 / fill_rate

        self.fill_rate = fill_rate
        if self.fill_rate <= 0:
            raise ValueError("Fill rate must be greater than 0.")

        self.last_timestamp = time.time()

    def consume(self, n: int=1) -> bool:
        self.tokens += (time.time() - self.last_timestamp) * self.fill_rate
        if n > self.tokens:
            raise RuntimeError("Not enough tokens for that action.")

        self.tokens -= n

        return True


class BucketManager:
    def __init__(self):
        # Dict of guild_id : tokenbucket
        self._buckets = {}

    def __call__(self, guild: discord.Guild) -> TokenBucket:
        """
        This function can throw KeyError if the given guild does
            not have a TokenBucket.
        :param guild: 
        :return: TokenBucket
        """
        return self._buckets[guild.id]

    def add_guild(self, guild: discord.Guild, bucket_args: list=None,
                  bucket: TokenBucket=None) -> TokenBucket:
        """
        You must provide EITHER bucket_kwargs or bucket!
        
        :param guild: 
        :param bucket_args: 
        :param bucket: 
        :return: 
        """
        if guild.id not in self._buckets:
            if bucket_args:
                self._buckets[guild.id] = TokenBucket(*bucket_args)
            elif bucket:
                self._buckets[guild.id] = bucket
            else:
                raise RuntimeError("You must provide either bucket_kwargs"
                                   " or bucket.")
        return self._buckets[guild.id]

    def remove_guild(self, guild: discord.Guild) -> bool:
        try:
            del self._buckets[guild.id]
        except KeyError:
            pass

        return True

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
        'role': 'AntiRaidMute',
        'is_under_raid': False,
        'raid_start_time': 0
    }

    def __init__(self, bot: commands.Bot):
        self._bot = bot

        self._config = Config.get_conf(self.__class__.__name__, 8927347832478324)

        self._config.register_guild(**self.default_settings)

        self._join_bucket_manager = BucketManager()

    def _enable(self, ctx: commands.Context, enable: bool=True):
        self._config.guild(ctx.guild).set("enabled", enable)

    @staticmethod
    def is_enabled(f: Callable) -> Callable:
        """
        Decorator that checks to see if AntiRaid is enabled.
        :param f: function
        :return: 
        """
        def pred(self, obj, *args, **kwargs):
            """
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
                f(self, obj, *args, **kwargs)
        return pred

    def _get_join_bucket_args(self, guild: discord.Guild) -> list:
        guild_settings = self._config.guild(guild)
        return [
            guild_settings.joins(),
            1 / guild_settings.join_seconds()
        ]

    @is_enabled
    def consume_join(self, member: discord.Member):
        enabled = self._config.guild(member.guild).enabled()
        if enabled:
            try:
                bucket = self._join_bucket_manager(member.guild)
            except KeyError:
                args = self._get_join_bucket_args(member.guild)
                bucket = self._join_bucket_manager.add_guild(
                    member.guild,
                    bucket_args=args
                )
            bucket.consume()

    @is_enabled
    def consume_message(self, message: discord.Message):
        pass

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

    async def on_member_join(self, member: discord.Member):
        self.consume_join(member)

    async def on_message(self, message: discord.Message):
        self.consume_message(message)


def maybe_create_default_server_settings():
    if not os.path.exists(AntiRaid.SETTINGS_PATH):
        pass


def setup(bot: commands.Bot):
    bot.add_cog(AntiRaid(bot))
