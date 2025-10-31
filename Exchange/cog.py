import random
import logging
import discord
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

    @app_commands.command(
        name="exchange",
        description="Exchange one of your balls for a random new one.",
    )
    @app_commands.describe(countryball="Select a ball from your collection to exchange.")
    async def exchange(
        self,
        interaction: discord.Interaction,
        countryball: BallInstanceTransform,
    ):
        """Exchange command for MarketDex."""
        user_id = interaction.user.id
        now = discord.utils.utcnow().timestamp()

        # cooldown
        if user_id in self.cooldowns and now - self.cooldowns[user_id] < 30:
            remaining = 30 - int(now - self.cooldowns[user_id])
            await interaction.response.send_message(
                f"⏳ You can exchange again in {remaining}s.", ephemeral=True
            )
            return
        self.cooldowns[user_id] = now

        if not countryball:
            await interaction.response.send_message("❌ That ball could not be found.")
            return

        player, _ = await Player.get_or_create(discord_id=user_id)
        chosen = await BallInstance.get_or_none(
            id=countryball.id, player=player
        ).prefetch_related("ball")

        if not chosen:
            await interaction.response.send_message("❌ You don't own that ball.")
            return

        confirm_view = ConfirmChoiceView(interaction)
        await interaction.response.send_message(
            f"Are you sure you want to exchange **{getattr(chosen.ball, 'country', 'Unknown')}**?",
            view=confirm_view,
        )
        await confirm_view.wait()
        if not confirm_view.value:
            return

        trade_objects = await TradeObject.filter(ballinstance_id=chosen.id)
        if trade_objects:
            try:
                deleted = await TradeObject.filter(ballinstance_id=chosen.id).delete()
                log.info(f"Deleted {deleted} TradeObject(s) for BallInstance {chosen.id}")
            except Exception as e:
                log.error(f"Failed deleting trade objects for {chosen.id}", exc_info=e)
                await interaction.followup.send(
                    f"❌ Cleanup failed: {e}", ephemeral=True
                )
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
                new_instance = await BallInstance.create(
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

        emoji = self.bot.get_emoji(getattr(new_ball, "emoji_id", 0))
        emoji_str = str(emoji) if emoji else ""
        old_name = getattr(chosen.ball, "country", "Unknown")
        new_name = getattr(new_ball, "country", "Unknown")

        file = None
        try:
            if hasattr(new_instance, "prepare_for_message"):
                content, file, _ = await new_instance.prepare_for_message(interaction)
        except Exception as e:
            log.warning("Failed to prepare card image: %s", e)

        embed = discord.Embed(
            title="Exchange Complete!",
            description=(
                f"**{interaction.user.display_name}** exchanged **{old_name}** for "
                f"**{emoji_str} {new_name}**!"
            ),
            color=discord.Color.gold(),
        )
        embed.add_field(
            name="New Stats",
            value=f"ATK {atk_bonus:+d}% | HP {hp_bonus:+d}%",
        )
        embed.set_footer(text="A fair trade... or was it?")

        if file:
            embed.set_image(url="attachment://card.png")
            file.filename = "card.png"
            await interaction.channel.send(embed=embed, file=file)
            file.close()
        else:
            await interaction.channel.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Exchange(bot))
