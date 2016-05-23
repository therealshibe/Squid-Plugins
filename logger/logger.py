import logging
from discord.ext import commands
from cogs.utils import checks
from cogs.utils.chat_formatting import box
from __main__ import send_cmd_help

try:
    import tabulate
except:
    tabulate = None

log = logging.getLogger("red.logger")
log.setLevel(logging.DEBUG)


class Logger:
    """Messes with the bot loggers"""

    def __init__(self, bot):
        self.bot = bot
        self.levels = [
            "debug",
            "warning",
            "critical",
            "info",
            "error",
            "notset"
        ]

    def _get_levels(self, loggers):
        ret = []
        for logger in loggers:
            logger_lvl = logging.getLogger(logger).getEffectiveLevel()
            ret.append(self._int_to_name(logger_lvl))
        log.debug("Level list:\n\t{}".format(ret))
        return ret

    def _get_loggers(self):
        ret = []
        for logname in logging.Logger.manager.loggerDict:
            ret.append(logname)
        ret = sorted(ret)
        return ret

    def _get_red_loggers(self):
        loggers = self._get_loggers()
        ret = []
        for logger in loggers:
            if logger.lower().startswith("red"):
                ret.append(logger)
        ret = sorted(ret)
        log.debug("Logger list:\n\t{}".format(ret))
        return ret

    def _int_to_name(self, level_int):
        if level_int == logging.CRITICAL:
            return "Critical"
        elif level_int == logging.ERROR:
            return "Error"
        elif level_int == logging.WARNING:
            return "Warning"
        elif level_int == logging.INFO:
            return "Info"
        elif level_int == logging.DEBUG:
            return "Debug"
        elif level_int == logging.NOTSET:
            return "Not set"
        return level_int

    def _name_to_level(self, level_str):
        try:
            level = int(level_str)
        except:
            pass
        else:
            return str(level)

        if level_str.lower() in self.levels:
            return getattr(logging, level_str.upper())

    @commands.group(pass_context=True)
    @checks.is_owner()
    async def logger(self, ctx):
        """Messes with the bot loggers"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @logger.command(pass_context=True, name="list")
    async def logger_list(self, ctx):
        """Lists logs and their levels."""
        loggers = self._get_red_loggers()
        levels = self._get_levels(loggers)
        ret = zip(loggers, levels)
        headers = ["Logger", "Level"]
        msg = tabulate.tabulate(ret, headers, tablefmt="psql")
        await self.bot.say(box(msg))

    @logger.command(pass_context=True, name="setlevel")
    async def logger_setlevel(self, ctx, name, level):
        """Sets level for a logger"""
        if name not in self._get_loggers():
            await self.bot.say("Invalid logger.")
            return
        elif name not in self._get_red_loggers():
            await self.bot.say("Not a Red logger.")
            return

        try:
            level = self._name_to_level(level)
        except:
            await self.bot.say("Bad level.")
        else:
            logger = logging.getLogger(name)
            logger.setLevel(level)
            await self.bot.say("{} set to logging.{}".format(
                name, self._int_to_name(level).upper()))


def setup(bot):
    if tabulate is None:
        raise RuntimeError("Must run `pip install tabulate` to use Logger.")
    n = Logger(bot)
    bot.add_cog(n)
