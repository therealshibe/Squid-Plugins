import discord
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from cogs.utils import checks
import os
import logging
import time

log = logging.getLogger("red.permissions")


class PermissionsError(Exception):
    """
    Base exception for all others in this module
    """


class BadCommand(PermissionsError):
    """
    Thrown when we can't decipher a command from string into a command object.
    """
    pass


class RoleNotFound(PermissionsError):
    """
    Thrown when we can't get a valid role from a list and given name
    """
    pass


class SpaceNotation(BadCommand):
    """
    Throw when, with some certainty, we can say that a command was space
        notated, which would only occur when some idiot...fishy...tries to
        surround a command in quotes.
    """
    pass


class Check:
    """
    This is what we're going to stick into the checks for Command objects
    """

    def __call__(self, ctx):
        pass


class Permissions:
    """
    The VERY important thing to note about this cog is that every command will
    be interpreted in dot notation instead of space notation (e.g how you call
    them from within Discord)
    """

    def __init__(self, bot):
        self.bot = bot

        # All the saved permission levels with role ID's
        self.perms_we_want = self._load_perms()

    def __unload(self):
        pass

    def _error_raise(exc):
        def deco(func):
            def pred(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    raise exc from e
            return pred
        return deco

    async def _error_responses(self, error, ctx):
        if isinstance(error, SpaceNotation):
            await self.bot.say("You just tried space notation, how about"
                               " you replace those spaces with dots and"
                               " try again?")
        elif isinstance(error, BadCommand):
            await self.bot.say("Command not found.")
        else:
            await self.bot.say("Unknown error: {}: {}".format(
                type(error).__name__, str(error)))
            log.exception("Error in {}".format(ctx.command.qualified_name),
                          exc_info=error)

    @_error_raise(BadCommand)
    def _get_command(self, cmd_string):
        cmd = cmd_string.split('.')
        ret = self.bot.commands[cmd.pop(0)]
        while len(cmd) > 0:
            ret = ret.commands[cmd.pop(0)]
        return ret

    def _get_ordered_role_list(self, server=None, roles=None):
        """
        First item in ordered list is @\u200Beveryone, e.g. the highest role
            in the Discord role heirarchy is last in this list.
        """
        if server is None and roles is None:
            raise PermissionsError("Must supply either server or role.")

        if server:
            roles = server.roles

        ordered_roles = sorted(roles, key=lambda r: r.position)

        log.debug("Ordered roles for sid {}:\n\t{}".format(server.id,
                                                           ordered_roles))

        return sorted(roles, key=lambda r: r.position)

    def _get_role(self, roles, role_string):
        role = discord.utils.find(
            lambda r: r.name.lower() == role_string.lower(), roles)

        if role is None:
            raise RoleNotFound(roles[0].server, role_string)

        return role

    def _get_role_from_id(self, server, roleid):
        try:
            roles = server.roles
        except AttributeError:
            server = self._get_server_from_id(server)
            try:
                roles = server.roles
            except AttributeError:
                raise RoleNotFound(server, roleid)

        role = discord.utils.get(roles, id=roleid)
        if role is None:
            raise RoleNotFound(server, roleid)
        return role

    def _get_server_from_id(self, serverid):
        return discord.utils.get(self.bot.servers, id=serverid)

    def _has_higher_role(self, member, role):
        server = member.server
        roles = self._get_ordered_role_list(server=server)
        try:
            role_index = roles.index(role)
        except ValueError:
            # Role isn't in the ordered role list
            return False

        higher_roles = roles[role_index + 1:]

        if any([r in higher_roles for r in member.roles]):
            return True
        return False

    def _is_allow(self, permission):
        if permission.startswith("+"):
            return True
        return False

    def _load_perms(self):
        try:
            ret = dataIO.load_json("data/permissions/perms.json")
        except:
            ret = {}
            os.mkdir("data/permissions")
            dataIO.save_json("data/permissions/perms.json", ret)
        return ret

    def resolve_permission(self, ctx):
        command = ctx.command.qualified_name.replace(' ', '.')
        server = ctx.message.server
        channel = ctx.message.channel
        roles = reversed(self._get_ordered_role_list(
            roles=ctx.message.author.roles))

        try:
            per_command = self.perms_we_want[command]
        except KeyError:
            return True

        try:
            per_server = per_command[server.id]
        except KeyError:
            # In this case the server is not in the perms we want to check
            #   therefore we're just gonna assume the default "allow"
            return True

        channel_perm_dict = per_server["CHANNELS"]
        role_perm_dict = per_server["ROLES"]

        if channel.id not in channel_perm_dict:
            # Again, assume default "allow"
            channel_perm = True
        else:
            # We know that an admin has set permission on this channel
            if self._is_allow(channel_perm_dict[channel.id]):
                channel_perm = True
            else:
                channel_perm = False

        for role in roles:
            if role.id in role_perm_dict:
                if self._is_allow(role_perm_dict[role.id]):
                    role_perm = True
                    break
                else:
                    role_perm = False
                    break
        else:
            # By doing this we let the channel perm override in the case of
            #   no role perms being set.
            role_perm = None

        has_perm = channel_perm or (role_perm is True)
        return has_perm

    def _save_perms(self):
        dataIO.save_json('data/permissions/perms.json', self.perms_we_want)

    def _set_role_allow(self, command, server, role):
        cmd_dot_name = command.qualified_name.replace(" ", ".")
        if cmd_dot_name not in self.perms_we_want:
            self.perms_we_want[cmd_dot_name] = {}
            self.perms_we_want[cmd_dot_name][server.id] = \
                {"CHANNELS": {}, "ROLES": {}}
        self.perms_we_want[cmd_dot_name][server.id]["ROLES"][role.id] = \
            "+{}".format(cmd_dot_name)
        self._save_perms()

    def _set_role_deny(self, command, server, role):
        cmd_dot_name = command.qualified_name.replace(" ", ".")
        if cmd_dot_name not in self.perms_we_want:
            self.perms_we_want[cmd_dot_name][server.id] = \
                {"CHANNELS": {}, "ROLES": {}}
        self.perms_we_want[cmd_dot_name][server.id]["ROLES"][role.id] = \
            "-{}".format(cmd_dot_name)
        self._save_perms()

    @commands.group(pass_context=True)
    @checks.serverowner_or_permissions(manage_roles=True)
    async def p(self, ctx):
        """Permissions manager"""
        if ctx.invoked_subcommand is None:
            return

    @p.error
    async def p_error(self, error, ctx):
        # Error is always gonna be commands.CommandError
        await self._error_responses(error.__cause__, ctx)

    @p.group(pass_context=True)
    async def channel(self, ctx):
        if ctx.invoked_subcommand is None or \
                isinstance(ctx.invoked_subcommand, commands.Group):
            return

    @channel.command(pass_context=True, name="allow")
    async def channel_allow(self, ctx, command, channel: discord.Channel):
        """Explicitly allows [command] to be used in [channel].

        Not really useful because role perm overrides channel perm"""
        pass

    @channel.command(pass_context=True, name="deny")
    async def channel_deny(self, ctx, command, channel: discord.Channel):
        """Explicitly denies [command] usage in [channel]

        Overridden by role based permissions"""
        pass

    @channel.command(pass_context=True, name="reset")
    async def channel_reset(self, ctx, command, channel: discord.Channel):
        """Resets permissions of [command] on [channel] to the default"""
        pass

    @p.group(pass_context=True)
    async def role(self, ctx):
        if ctx.invoked_subcommand is None or \
                isinstance(ctx.invoked_subcommand, commands.Group):
            return

    @role.command(pass_context=True, name="allow")
    async def role_allow(self, ctx, command, *, role):
        """Explicitly allows [command] to be used by [role] server wide

        This OVERRIDES channel based permissions"""
        server = ctx.message.server
        command_obj = self._get_command(command)
        role = self._get_role(server.roles, role)
        await self.bot.say("{} {}".format(command_obj.qualified_name,
                                          role.name))

        self._set_role_allow(command_obj, server, role)

    @role.command(pass_context=True, name="deny")
    async def role_deny(self, ctx, command, *, role):
        """Explicitly denies [command] usage by [role] server wide

        This OVERRIDES channel based permissions"""
        pass

    @role.command(pass_context=True, name="reset")
    async def role_reset(self, ctx, command, *, role):
        """Reset permissions of [role] on [command] to the default"""
        pass


def setup(bot):
    n = Permissions(bot)
    bot.add_cog(n)
