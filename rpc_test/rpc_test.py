from discord.ext import commands

from aiohttp_json_rpc import JsonRpcClient
import logging

from redbot.core.utils.chat_formatting import box

log = logging.getLogger('red.RpcTest')


class RpcTest:
    def __init__(self):
        self.rpc_server = None  # type: JsonRpcClient

    async def ensure_connected(self):
        if self.rpc_server is None:
            self.rpc_server = JsonRpcClient(logger=log)
            await self.rpc_server.connect('127.0.0.1', 8080, '/rpc')

    @commands.command()
    async def list_methods(self, ctx):
        await self.ensure_connected()

        methods = await self.rpc_server.get_methods()

        await ctx.send(box('\n'.join(methods)))

    @commands.command()
    async def get_cogs(self, ctx):
        await self.ensure_connected()

        cogs = await self.rpc_server.call('bot__rpc__cogs')

        await ctx.send(box('\n'.join(cogs)))

    @commands.command()
    async def rpc_call(self, ctx, method_name, *args):
        await self.ensure_connected()
        result = await self.rpc_server.call(method_name, params=args, timeout=5)

        if result is not None:
            await ctx.send(box(result))
        else:
            await ctx.send('No response.')
