import discord
import random
import logging
from discord import app_commands
from discord.ext import commands
from tortoise.transactions import in_transaction

from ballsdex.core.models import Player, Ball, BallInstance, TradeObject
from ballsdex.core.utils.transformers import BallInstanceTransform
from ballsdex.core.utils.buttons import ConfirmChoiceView

log = logging.getLogger("ballsdex.packages.exchange")


@app_commands.guild_only()
class Exchange(commands.Cog):
    """Exchange one of your owned balls for a random new one."""

    def __init__(self, bot):
        self.bot = bot
        self.cooldowns = {}

    @app_commands.command(name="exchange", description="Exchange one of your balls for a random new one.")
    @app_commands.describe(countryball="Select a ball from your collection to exchange.")
    async def exchange(self, interaction: discord.Interaction, countryball: BallInstanceTransform):
        user_id = interaction.user.id
        now = discord.utils.utcnow().timestamp()

        if user_id in self.cooldowns and now - self.cooldowns[user_id] < 30:
            remaining = 30 - int(now - self.cooldowns[user_id])
            await interaction.response.send_message(
                f"⏳ You can exchange again in {remaining}s.", ephemeral=True
            )
            return
        self.cooldowns[user_id] = now

        if not countryball:
            await interaction.response.send_message("❌ That ball could not be found.", ephemeral=True)
            return

        player, _ = await Player.get_or_create(discord_id=user_id)
        chosen = await BallInstance.get_or_none(id=countryball.id, player=player).prefetch_related("ball")
        if not chosen:
            await interaction.response.send_message("❌ You don't own that ball.", ephemeral=True)
            return

        confirm_view = ConfirmChoiceView(interaction)
        await interaction.response.send_message(
            f"Are you sure you want to exchange **{getattr(chosen.ball, 'country', getattr(chosen.ball, 'name', 'Unknown'))}**?",
            view=confirm_view,
        )
        await confirm_view.wait()
        if not confirm_view.value:
            return

        enabled_balls = await Ball.filter(enabled=True)
        if not enabled_balls:
            await interaction.followup.send("⚠️ No enabled balls found.")
            return

        new_ball = random.choice(enabled_balls)
        atk_bonus = random.randint(-20, 20)
        hp_bonus = random.randint(-20, 20)

        try:
            async with in_transaction():
                await TradeObject.filter(ballinstance_id=chosen.id).delete()

                await BallInstance.create(
                    player=player,
                    ball=new_ball,
                    attack_bonus=atk_bonus,
                    health_bonus=hp_bonus,
                )

                await chosen.delete()
        except Exception as e:
            log.error("Exchange failed", exc_info=e)
            await interaction.followup.send(f"❌ Exchange failed: {e}")
            return

        old_name = getattr(chosen.ball, "country", getattr(chosen.ball, "name", "Unknown"))
        new_name = getattr(new_ball, "country", getattr(new_ball, "name", "Unknown"))
        emoji = self.bot.get_emoji(getattr(new_ball, "emoji_id", None)) or "🎲"

        image_url = getattr(new_ball, "image_url", None) or getattr(new_ball, "image", None)
        if not image_url and hasattr(new_ball, "card_url"):
            image_url = new_ball.card_url

        embed = discord.Embed(
            title="Exchange Complete!",
            description=f"**{interaction.user.display_name}** exchanged **{old_name}** for {emoji} **{new_name}**!",
            color=discord.Color.gold(),
        )
        embed.add_field(name="New Stats", value=f"ATK {atk_bonus:+}% | HP {hp_bonus:+}%")
        embed.set_footer(text="A fair trade... or was it?")
        if image_url:
            embed.set_image(url=image_url)

        await interaction.followup.send(embed=embed)
