from .cog import Merchant

async def setup(bot):
    await bot.add_cog(Merchant(bot))
