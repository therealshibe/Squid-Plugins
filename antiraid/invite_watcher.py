from collections import namedtuple

import discord
import time


class InviteWatcher:
    def __init__(self, guild: discord.Guild):
        self._guild_id = guild.id
