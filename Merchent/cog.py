import discord
import random
import tomllib
import os
import json
import time

from discord import app_commands
from discord.ext import commands
from ballsdex.core.models import Ball, balls  # ✅ use global cache


CONFIG_PATH = "ballsdex/packages/merchant/config.toml"
DATA_PATH = "ballsdex/packages/merchant/merchant_data.json"


def load_config():
    with open(CONFIG_PATH, "rb") as f:
        return tomllib.load(f)


def load_data():
    if not os.path.exists(DATA_PATH):
        with open(DATA_PATH, "w") as f:
            json.dump({}, f)
    with open(DATA_PATH, "r") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_PATH, "w") as f:
        json.dump(data, f, indent=4)


class Merchant(commands.GroupCog, group_name="merchant"):
    """Merchant system for limited-time Market Balls."""

    def __init__(self, bot):
        self.bot = bot
        self.config = load_config()
        self.shop_items = []
        self.last_refresh = 0
        self.refresh_shop()

    def refresh_shop(self):
        """Refreshes shop items daily based on rarity config."""
        min_rarity = self.config.get("min_rarity", 1)
        max_rarity = self.config.get("max_rarity", 200)

        available_balls = [
            ball for ball in balls.values()
            if ball.enabled and min_rarity <= ball.rarity <= max_rarity
        ]

        if not available_balls:
            self.shop_items = []
            return

        self.shop_items = random.sample(available_balls, min(5, len(available_balls)))
        self.last_refresh = time.time()

    @app_commands.command(name="view", description="View the merchant's current items.")
    async def view(self, interaction: discord.Interaction):
        """Show available items and buttons to buy."""
        currency = self.config.get("currency_name", "Market Tokens")

        # Refresh every 24 hours
        if time.time() - self.last_refresh > 86400:
            self.refresh_shop()

        if not self.shop_items:
            await interaction.response.send_message(
                "The merchant is resting right now. Check back later!"
            )
            return

        embed = discord.Embed(
            title="🛍️ Merchant’s Market",
            description=f"Spend your {currency} on exclusive Market Balls!\n"
                        f"Shop refreshes every **24 hours**.",
            color=discord.Color.gold()
        )

        view = discord.ui.View()
        for ball in self.shop_items:
            emoji = interaction.client.get_emoji(ball.emoji_id)
            name = f"{emoji} {ball.country}" if emoji else ball.country

            # Inverted rarity pricing: rarer = cheaper
            max_rarity = 200
            min_rarity = 1
            max_price = 50  # T5 cost
            min_price = 2   # T200 cost
            price = int(min_price + (max_rarity - ball.rarity) * (max_price - min_price) / (max_rarity - min_rarity))

            embed.add_field(
                name=f"{name}",
                value=f"Rarity: {ball.rarity}\n💰 **{price} {currency}**",
                inline=False,
            )

            button = discord.ui.Button(label=f"Buy {ball.country}", style=discord.ButtonStyle.green)

            async def buy_callback(inner_interaction, ball=ball, price=price):
                data = load_data()
                uid = str(inner_interaction.user.id)
                balance = data.get(uid, {}).get("balance", 0)

                if balance < price:
                    await inner_interaction.response.send_message(
                        f"❌ You need **{price - balance}** more {currency}!"
                    )
                    return

                data.setdefault(uid, {"balance": 0, "last_claim": 0})
                data[uid]["balance"] -= price
                save_data(data)

                emoji = inner_interaction.client.get_emoji(ball.emoji_id)
                emoji_display = emoji if emoji else "🎁"
                await inner_interaction.response.send_message(
                    f"{emoji_display} {inner_interaction.user.mention} bought **{ball.country}** for **{price} {currency}**!"
                )

            button.callback = buy_callback
            view.add_item(button)

        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="balance", description="Check your Market Token balance.")
    async def balance(self, interaction: discord.Interaction):
        """Show user token balance and time until next daily."""
        data = load_data()
        user_id = str(interaction.user.id)
        currency = self.config.get("currency_name", "Market Tokens")
        user_data = data.get(user_id, {"balance": 0, "last_claim": 0})
        balance = user_data.get("balance", 0)

        now = time.time()
        remaining = max(0, 86400 - (now - user_data.get("last_claim", 0)))
        if remaining > 0:
            hours = int(remaining // 3600)
            minutes = int((remaining % 3600) // 60)
            cooldown_text = f"Next daily in {hours}h {minutes}m"
        else:
            cooldown_text = "✅ Daily available now!"

        embed = discord.Embed(
            title=f"{interaction.user.display_name}'s Wallet",
            description=f"💰 **{balance} {currency}**\n{cooldown_text}",
            color=discord.Color.blurple()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="daily", description="Claim your daily Market Tokens.")
    async def daily(self, interaction: discord.Interaction):
        """Users can claim daily tokens once every 24 hours."""
        data = load_data()
        user_id = str(interaction.user.id)
        currency = self.config.get("currency_name", "Market Tokens")

        now = time.time()
        user_data = data.get(user_id, {"balance": 0, "last_claim": 0})
        last_claim = user_data.get("last_claim", 0)

        if now - last_claim < 86400:  # 24 hours
            remaining = int(86400 - (now - last_claim))
            hours = remaining // 3600
            minutes = (remaining % 3600) // 60
            await interaction.response.send_message(
                f"🕓 {interaction.user.mention} can claim again in {hours}h {minutes}m."
            )
            return

        reward = random.randint(3, 10)
        user_data["balance"] += reward
        user_data["last_claim"] = now
        data[user_id] = user_data
        save_data(data)

        await interaction.response.send_message(
            f"🎁 {interaction.user.mention} has claimed **{reward} {currency}**! Come back tomorrow for more."
        )

    @app_commands.command(name="give", description="Give Market Tokens to a user (Admin only).")
    @app_commands.describe(user="User to give tokens to.", amount="How many tokens to give.")
    async def give(self, interaction: discord.Interaction, user: discord.User, amount: int):
        """Admin-only command to give tokens."""
        config = self.config
        admin_roles = config.get("admin_roles", [])
        currency = config.get("currency_name", "Market Tokens")

        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message("❌ This command must be used in a server.", ephemeral=True)
            return

        if not any(role.id in admin_roles for role in interaction.user.roles):
            await interaction.response.send_message("🚫 You don’t have permission to do that.", ephemeral=True)
            return

        data = load_data()
        uid = str(user.id)
        data.setdefault(uid, {"balance": 0, "last_claim": 0})
        data[uid]["balance"] += amount
        save_data(data)

        await interaction.response.send_message(
            f"✅ {interaction.user.mention} gave **{amount} {currency}** to {user.mention}!"
        )

        try:
            await user.send(f"💰 You’ve received **{amount} {currency}** from an admin!")
        except discord.Forbidden:
            pass


async def setup(bot):
    await bot.add_cog(Merchant(bot))

