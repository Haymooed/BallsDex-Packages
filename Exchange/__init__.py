from .cog import Exchange

async def setup(bot):
    await bot.add_cog(Exchange(bot))
