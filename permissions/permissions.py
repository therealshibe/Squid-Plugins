import discord
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from cogs.utils import checks
import os
import logging

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

        # All the checks we've added into Command objects
        self.perm_check_map = {}

    def _check(self, serverid, roleid):
        def has_higher_role(member, role):
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

        def pred(ctx):
            server = self._get_server_from_id(serverid)
            role = self._get_role_from_id(roleid)
            msg = "Check on `{}`".format(ctx.command.qualified_name)
            # Ignore in pm
            if ctx.message.channel.is_private:
                return True

            # Our old server doesn't exist
            if server not in ctx.bot.servers:
                log.debug(msg + " failed: server not in bot serverlist")
                return True

            # This is not the server you are looking for
            if ctx.message.server != server:
                log.debug(msg + " failed: check server does not equal"
                                " current server")
                return True

            # Role has been deleted
            if role not in ctx.message.server.roles:
                log.debug(msg + " failed: role has been deleted")
                return True

            if role in ctx.message.author.roles or \
                    has_higher_role(ctx.message.author, role):
                log.debug(msg + " succeeded: aid {} has permissions".format(
                    ctx.message.author.id))
                return True
            else:
                log.debug(
                    msg + " succeeded: aid {} does not have permission".format(
                        ctx.message.author.id))
                return False
        return pred

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
            await self.bot.say("Unknown error: {}".format(type(error)))

    @_error_raise(BadCommand)
    def _get_command(self, cmd_string):
        cmd = cmd_string.split('.')
        ret = self.bot.commands[cmd.pop(0)]
        while len(cmd) > 0:
            ret = ret.commands[cmd.pop(0)]
        return ret

    def _get_ordered_role_list(self, server=None, roles=None):
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

    def _load_perms(self):
        try:
            ret = dataIO.load_json("data/permissions/perms.json")
        except:
            ret = {}
            os.mkdir("data/permissions")
            dataIO.save_json("data/permissions/perms.json", ret)
        return ret

    @commands.group(pass_context=True)
    @checks.serverowner_or_permissions(manage_roles=True)
    async def p(self, ctx):
        """Permissions manager"""
        if ctx.invoked_subcommand is None:
            return

    @p.command(pass_context=True, name="set")
    async def _set(self, ctx, command, *, role):
        """Require a command to (at minimum) be run by the specified role"""
        server = ctx.message.server
        command_obj = self._get_command(command)
        role = self._get_role(server.roles, role)
        await self.bot.say("{} {}".format(command_obj.qualified_name,
                                          role.name))

    @_set.error
    async def _set_error(self, error, ctx):
        # Error is always gonna be commands.CommandError
        await self._error_responses(error.__cause__, ctx)


def setup(bot):
    n = Permissions(bot)
    bot.add_cog(n)
