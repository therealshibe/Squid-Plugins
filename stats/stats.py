from discord.ext import commands
from cogs.utils import checks
from cogs.utils.dataIO import dataIO
import logging
import os
from __main__ import send_cmd_help

try:
    import datadog
    from datadog import statsd
except:
    datadog = None

log = logging.getLogger("red.stats")


class Stats:
    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json('data/stats/settings.json')
        self._is_initialized = False

    def _configured(self):
        if self._is_initialized:
            return True
        return self._initialize

    def _initialize(self):
        if "APIKEY" not in self.settings or "APPKEY" not in self.settings:
            return False

        apikey = self.settings.get("APIKEY")
        appkey = self.settings.get("APPKEY")

        datadog.initialize(api_key=apikey, app_key=appkey,
                           statsd_host='localhost', statsd_port=8125)
        self._is_initialized = True
        return True

    def _increment(self, metric, *args, **kwargs):
        if not self._configured():
            return
        statsd.increment(metric, *args, **kwargs)

    def _save_settings(self):
        dataIO.save_json('data/stats/settings.json', self.settings)

    def _set_api_key(self, key):
        self.settings["APIKEY"] = key
        self._save_settings()

    def _set_app_key(self, key):
        self.settings["APPKEY"] = key
        self._save_settings()

    @commands.group(pass_context=True)
    async def stats(self, ctx):
        """Bot stat tracker for Datadog"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @commands.group(pass_context=True)
    @checks.is_owner()
    async def statset(self, ctx):
        """Manage stats settings."""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @statset.command(name="apikey", pm_only=True)
    async def statset_apikey(self, key):
        """Sets datadog API key"""
        self._set_api_key(key)
        await self.bot.say("API key successfully set.")

    @statset.command(name="appkey", pm_only=True)
    async def statset_appkey(self, key):
        """Sets datadog APP key"""
        self._set_app_key(key)
        await self.bot.say("APP key successfully set.")

    async def error(self, event, *args, **kwargs):
        self._increment("red.error")

    async def message(self, message):
        self._increment("red.message")

    async def socket_raw_receive(self, msg):
        self._increment("red.socket.raw.receive")

    async def socket_raw_send(self, msg):
        self._increment("red.socket.raw.send")

    async def message_delete(self, message):
        self._increment("red.message.delete")

    async def message_edit(self, before, after):
        self._increment("red.message.edit")

    async def channel_delete(self, channel):
        self._increment("red.channel.delete")

    async def channel_create(self, channel):
        self._increment("red.channel.create")

    async def channel_update(self, before, after):
        self._increment("red.channel.update")

    async def member_join(self, member):
        self._increment("red.member.join")

    async def member_remove(self, member):
        self._increment("red.member.remove")

    async def member_update(self, before, after):
        self._increment("red.member.update")

    async def server_join(self, server):
        self._increment("red.server.join")

    async def server_remove(self, server):
        self._increment("red.server.remove")

    async def server_update(self, before, after):
        self._increment("red.server.update")

    async def server_role_create(self, role):
        self._increment("red.server.role.create")

    async def server_role_delete(self, role):
        self._increment("red.server.role.delete")

    async def server_role_update(self, before, after):
        self._increment("red.server.role.update")

    async def voice_state_update(self, before, after):
        self._increment("red.voice.state.update")

    async def member_ban(self, member):
        self._increment("red.member.ban")

    async def member_unban(self, server, user):
        self._increment("red.member.unban")

    async def typing(self, channel, user, when):
        self._increment("red.typing")

    async def command(self, command, ctx):
        self._increment("red.command")

    async def command_error(self, error, ctx):
        self._increment("red.command.error")

    async def command_completion(self, command, ctx):
        self._increment("red.command.completion")


def check_files():
    if not os.path.exists('data/stats/settings.json'):
        try:
            os.mkdir('data/stats')
        except:
            pass
        dataIO.save_json('data/stats/settings.json', {})


def setup(bot):
    if datadog is None:
        raise RuntimeError("You must `pip install datadog` to use this cog.")
    check_files()
    n = Stats(bot)
    bot.add_cog(n)
    bot.add_listener(n.error, 'on_error')
    bot.add_listener(n.message, 'on_message')
    bot.add_listener(n.socket_raw_receive, 'on_socket_raw_receive')
    bot.add_listener(n.socket_raw_send, 'on_socket_raw_send')
    bot.add_listener(n.message_delete, 'on_message_delete')
    bot.add_listener(n.message_edit, 'on_message_edit')
    bot.add_listener(n.channel_delete, 'on_channel_delete')
    bot.add_listener(n.channel_create, 'on_channel_create')
    bot.add_listener(n.channel_update, 'on_channel_update')
    bot.add_listener(n.member_join, 'on_member_join')
    bot.add_listener(n.member_remove, 'on_member_remove')
    bot.add_listener(n.member_update, 'on_member_update')
    bot.add_listener(n.member_ban, 'on_member_ban')
    bot.add_listener(n.member_unban, 'on_member_unban')
    bot.add_listener(n.server_join, 'on_server_join')
    bot.add_listener(n.server_remove, 'on_server_remove')
    bot.add_listener(n.server_update, 'on_server_update')
    bot.add_listener(n.server_role_create, 'on_server_role_create')
    bot.add_listener(n.server_role_delete, 'on_server_role_delete')
    bot.add_listener(n.server_role_update, 'on_server_role_update')
    bot.add_listener(n.voice_state_update, 'on_voice_state_update')
    bot.add_listener(n.typing, 'on_typing')
    bot.add_listener(n.command, 'on_command')
    bot.add_listener(n.command_error, 'on_command_error')
    bot.add_listener(n.command_completion, 'on_command_completion')
