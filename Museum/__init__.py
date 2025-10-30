from .cog import Museum

async def setup(bot):
    await bot.add_cog(Museum(bot))
