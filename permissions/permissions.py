import discord
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from cogs.utils import checks
import os


class BadCommand(Exception):
    """
    Thrown when we can't decipher a command from string into a command object.
    """
    pass


class RoleNotFound(Exception):
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
        self.perms = self._load_perms()

    def _load_perms(self):
        try:
            ret = dataIO.load_json("data/permissions/perms.json")
        except:
            ret = {}
            os.mkdir("data/permissions")
            dataIO.save_json("data/permissions/perms.json", ret)
        return ret

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

    def _get_role(self, roles, role_string):
        role = discord.utils.find(
            lambda r: r.name.lower() == role_string.lower(), roles)

        if role is None:
            raise RoleNotFound(roles[0].server, role_string)

    @commands.group(pass_context=True)
    @checks.serverowner_or_permissions(manage_roles=True)
    async def p(self, ctx):
        if ctx.invoked_subcommand is None:
            return

    @p.command(pass_context=True, name="set")
    async def _set(self, ctx, command, *, role):
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
