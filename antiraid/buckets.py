from collections import namedtuple
from .invite_watcher import InviteWatcher

import discord
import time


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

    def consume(self, n: int = 1) -> bool:
        self.tokens += (time.time() - self.last_timestamp) * self.fill_rate
        if n > self.tokens:
            raise RuntimeError("Not enough tokens for that action.")

        self.tokens -= n

        return True


class JoinBucket(TokenBucket):
    def __init__(self, guild: discord.Guild, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._invite_counter = InviteWatcher(guild)

    def consume_join(self, guild: discord.Guild, n: int = 1):
        super().consume(n)
        self._invite_counter.recount(guild)


class BucketManager:
    def __init__(self, bucket_type=TokenBucket):
        # Dict of guild_id : tokenbucket
        self._buckets = {}
        self._bucket_type = bucket_type

        self.fake_guild = namedtuple("FakeGuild", "id")

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
                self._buckets[guild.id] = self._bucket_type(*bucket_args)
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

    def add_member(self, member: discord.Member, bucket_args: list=None,
                   bucket: TokenBucket=None) -> TokenBucket:
        combined_id = member.guild.id + member.id
        # noinspection PyTypeChecker
        return self.add_guild(self.fake_guild(combined_id),
                              bucket_args=bucket_args, bucket=bucket)

    def remove_member(self, member: discord.Member) -> bool:
        combined_id = member.guild.id + member.id
        # noinspection PyTypeChecker
        return self.remove_member(self.fake_guild(combined_id))
