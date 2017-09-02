from typing import List, Union

import discord
from discord.ext import commands

from core import Config
from core.bot import Red

from .converters import RegisteredMessage


class ReactRole:
    """
    This cog enables role assignment/removal based on reactions to specific
    messages.
    """

    def __init__(self, red: Red):
        self.bot = red
        self.config = Config.get_conf(self, 3203948230954902384)
        self.config.register_global(
            message_ids=[],
            details={}  # This is going to be a dict of message ID -> {emoji: [role_id]}
        )

    async def message_list(self) -> List[int]:
        """
        Helper method to get the list of watched message IDs.

        :return:
            A list of integer message IDs.
        :rtype:
            List[int]
        """
        return await self.config.message_ids()

    async def set_message_list(self, id_list: List[int]):
        """
        Helper method to set the list of watched message IDs.

        :param id_list:
        :return:
        """
        await self.config.message_ids.set(id_list)

    async def is_registered(self, message_id: int) -> bool:
        """
        Determines if a message ID has been registered.

        :param message_id:
        :return:
        """
        return message_id in await self.message_list()

    async def add_reactrole(self, message_id: int, emoji: discord.Emoji, role: discord.Role):
        """
        Adds a react|role combo.

        :param str message_id:
        :param discord.Emoji emoji:
        :param discord.Role role:
        """
        details = await self.config.details.get_attr(str(message_id), default={})

        role_list = details.get(str(emoji.id), [])
        role_list.append(role.id)

        details[str(emoji.id)] = role_list

        await self.config.details.get_attr(str(message_id), resolve=False).set(details)

    async def has_reactrole_combo(self, message_id: int, emoji_id: int)\
            -> (bool, Union[List[int], None]):
        """
        Determines if there is an existing react|role combo for a given message
        and emoji ID.

        :param int message_id:
        :param int emoji_id:
        :return:
        """
        if not await self.is_registered(message_id):
            return False

        details = await self.config.details.get_attr(str(message_id), default={})
        if str(emoji_id) not in details:
            return False, None
        return True, details[str(emoji_id)]

    def _get_member(self, channel_id: int, user_id: int) -> discord.Member:
        """
        Tries to get a member with the given user ID from the guild that has
        the given channel ID.

        :param int channel_id:
        :param int user_id:
        :rtype:
            discord.Member
        :raises LookupError:
            If no such channel or member can be found.
        """
        channel = self.bot.get_channel(channel_id)
        try:
            member = channel.guild.get_member(user_id)
        except AttributeError as e:
            raise LookupError("No channel found.") from e

        if member is None:
            raise LookupError("No member found.")

        return member

    def _get_role(self, guild: discord.Guild, role_id: int) -> discord.Role:
        """
        Gets a role object from the given guild with the given ID.

        :param discord.Guild guild:
        :param int role_id:
        :rtype:
            discord.Role
        :raises LookupError:
            If no such role exists.
        """
        role = discord.utils.get(guild.roles, id=role_id)

        if role is None:
            raise LookupError("No role found.")

        return role

    @commands.group()
    async def reactrole(self, ctx: commands.Context):
        """
        Base command for this cog. Check help for the commands list.
        """
        if ctx.invoked_subcommand is None:
            await ctx.bot.send_cmd_help(ctx)

    @reactrole.command()
    async def addmessage(self, ctx: commands.Context, message_id: int):
        """
        Registers a message to watch reactions for.
        """
        curr_ids = await self.message_list()
        if message_id not in curr_ids:
            curr_ids.append(message_id)
            await self.set_message_list(curr_ids)

        await ctx.send("Message ID registered.")

    @reactrole.command()
    async def removemessage(self, ctx: commands.Context, message_id: int):
        """
        Unregisters a watched message.
        """
        curr_ids = await self.message_list()
        if message_id in curr_ids:
            curr_ids.remove(message_id)
            await self.set_message_list(curr_ids)

        await ctx.send("Message ID unregistered.")

    @reactrole.command()
    async def addreactrole(self, ctx: commands.Context, message_id: RegisteredMessage,
                           reaction: discord.Emoji, role: discord.Role):
        """
        Adds a reaction|role combination to a registered message.
        """
        # noinspection PyTypeChecker
        await self.add_reactrole(message_id, reaction, role)

        await ctx.send("React|Role combo added.")

    async def on_raw_reaction_add(self, emoji: discord.PartialReactionEmoji,
                                  message_id: int, channel_id: int, user_id: int):
        """
        Event handler for long term reaction watching.

        :param discord.PartialReactionEmoji emoji:
        :param int message_id:
        :param int channel_id:
        :param int user_id:
        :return:
        """
        has_reactrole, role_ids = await self.has_reactrole_combo(message_id, emoji.id)

        if not has_reactrole:
            return

        try:
            member = self._get_member(channel_id, user_id)
        except LookupError:
            return

        try:
            roles = [self._get_role(member.guild, role_id) for role_id in role_ids]
        except LookupError:
            return

        try:
            await member.add_roles(*roles)
        except discord.Forbidden:
            pass

    async def on_raw_reaction_remove(self, emoji: discord.PartialReactionEmoji,
                                     message_id: int, channel_id: int, user_id: int):
        """
        Event handler for long term reaction watching.

        :param discord.PartialReactionEmoji emoji:
        :param int message_id:
        :param int channel_id:
        :param int user_id:
        :return:
        """
        has_reactrole, role_ids = await self.has_reactrole_combo(message_id, emoji.id)

        if not has_reactrole:
            return

        try:
            member = self._get_member(channel_id, user_id)
        except LookupError:
            return

        try:
            roles = [self._get_role(member.guild, role_id) for role_id in role_ids]
        except LookupError:
            return

        try:
            await member.remove_roles(*roles)
        except discord.Forbidden:
            pass
