from .rpc_test import RpcTest


def setup(bot):
    bot.add_cog(RpcTest())
