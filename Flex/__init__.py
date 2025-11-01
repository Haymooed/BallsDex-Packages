from .cog import Flex

async def setup(bot):
    await bot.add_cog(Flex(bot))

