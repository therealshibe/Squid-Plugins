import discord
from discord.ext import commands
from cogs.utils import checks
from cogs.utils.dataIO import dataIO
import logging
import os
import sys
import asyncio
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
        return self._initialize()

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

    def _tag_generator(self, *args, **kwargs):
        ret = [str(a) for a in args]
        for key, val in kwargs.items():
            ret.append("{}:{}".format(str(key), str(val)))
        return ret

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

    async def alive(self):
        while self == self.bot.get_cog('Stats'):
            statsd.service_check("red.alive", datadog.DogStatsd.OK)
            await asyncio.sleep(5)

    async def error(self, event, *args, **kwargs):
        print("errord")
        exc_type, value, tb = sys.exc_info()
        extra = {}
        if exc_type is discord.errors.HTTPException:
            extra["httpstatus"] = value.response.status
            extra["message"] = value.message
        tags = self._tag_generator(event=event, type=exc_type, **extra)
        self._increment("red.error", tags=tags)

    async def message(self, message):
        tags = self._tag_generator(serverid=message.server.id,
                                   channelid=message.channel.id,
                                   authorid=message.author.id)
        self._increment("red.message", tags=tags)

    async def socket_raw_receive(self, msg):
        self._increment("red.socket.raw.receive")

    async def socket_raw_send(self, msg):
        self._increment("red.socket.raw.send")

    async def message_delete(self, message):
        tags = self._tag_generator(serverid=message.server.id,
                                   channelid=message.channel.id,
                                   authorid=message.author.id)
        self._increment("red.message.delete", tags=tags)

    async def message_edit(self, before, after):
        tags = self._tag_generator(serverid=after.server.id,
                                   channelid=after.channel.id,
                                   authorid=after.author.id)
        self._increment("red.message.edit", tags=tags)

    async def channel_delete(self, channel):
        self._increment("red.channel.delete")

    async def channel_create(self, channel):
        self._increment("red.channel.create")

    async def channel_update(self, before, after):
        self._increment("red.channel.update")

    async def member_join(self, member):
        tags = self._tag_generator(serverid=member.server.id,
                                   authorid=member.id)
        self._increment("red.member.join", tags=tags)

    async def member_remove(self, member):
        tags = self._tag_generator(serverid=member.server.id,
                                   authorid=member.id)
        self._increment("red.member.remove", tags=tags)

    async def member_update(self, before, after):
        extra = {}
        if before.status != after.status:
            if after.status == discord.Status.online:
                extra["status"] = "online"
            elif after.status == discord.Status.idle:
                extra["status"] = "idle"
            else:
                extra["status"] = "offline"
        tags = self._tag_generator(**extra)
        self._increment("red.member.update", tags=tags)

    async def server_join(self, server):
        tags = self._tag_generator(serverid=server.id)
        self._increment("red.server.join", tags=tags)

    async def server_remove(self, server):
        tags = self._tag_generator(serverid=server.id)
        self._increment("red.server.remove", tags=tags)

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
        tags = self._tag_generator(serverid=member.server.id,
                                   authorid=member.id)
        self._increment("red.member.ban", tags=tags)

    async def member_unban(self, server, user):
        tags = self._tag_generator(serverid=server.id,
                                   authorid=user.id)
        self._increment("red.member.unban", tags=tags)

    async def typing(self, channel, user, when):
        self._increment("red.typing")

    async def command(self, command, ctx):
        tags = self._tag_generator(command=command.name,
                                   invoked_subcommand=ctx.invoked_subcommand,
                                   serverid=ctx.message.server.id,
                                   authorid=ctx.message.author.id)
        self._increment("red.command", tags=tags)

    async def command_error(self, error, ctx):
        exc_type, value, tb = sys.exc_info()
        tags = self._tag_generator(type=exc_type,
                                   serverid=ctx.message.server.id,
                                   authorid=ctx.message.author.id,
                                   command=ctx.invoked_with)
        self._increment("red.command.error", tags=tags)

    async def command_completion(self, command, ctx):
        tags = self._tag_generator(command=command.name,
                                   invoked_subcommand=ctx.invoked_subcommand,
                                   serverid=ctx.message.server.id,
                                   authorid=ctx.message.author.id)
        self._increment("red.command.completion", tags=tags)


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
    bot.loop.ensure_future(n.alive())
