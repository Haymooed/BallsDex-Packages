import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional

# Temporary in-memory DB; replace with your ORM / persistent storage
museum_db = {}  # {user_id: [card_ids]}

class Museum(commands.Cog):
    """A cog for managing users' museum displays."""

    def __init__(self, bot):
        self.bot = bot


    def get_user_museum(self, user_id: int):
        """Retrieve a user's museum display safely."""
        return museum_db.get(user_id, [])

    def set_user_museum(self, user_id: int, cards: list[str]):
        """Save a user's museum display safely."""
        museum_db[user_id] = cards

    async def send_error(self, interaction: discord.Interaction, message: str):
        """Uniform error message with styling."""
        embed = discord.Embed(
            title="⚠️ Error",
            description=message,
            colour=discord.Colour.red()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


    @app_commands.command(name="museum_view", description="View someone's museum display.")
    @app_commands.describe(user="The user whose museum you want to view.")
    async def museum_view(self, interaction: discord.Interaction, user: Optional[discord.User] = None):
        try:
            user = user or interaction.user
            cards = self.get_user_museum(user.id)

            if not cards:
                await interaction.response.send_message(
                    f"{user.display_name} has no cards displayed in their museum!",
                    ephemeral=True
                )
                return

            embeds = []
            for i, card_id in enumerate(cards, start=1):
                embed = discord.Embed(
                    title=f"{user.display_name}'s Museum — Card {i}/{len(cards)}",
                    description=f"🖼️ Displayed Card ID: `{card_id}`",
                    colour=discord.Colour.gold()
                )
                embed.set_footer(text="Use arrows below to navigate between cards.")
                embeds.append(embed)

            current_page = 0

            class Paginator(discord.ui.View):
                def __init__(self):
                    super().__init__(timeout=90)

                @discord.ui.button(label="◀️", style=discord.ButtonStyle.secondary)
                async def previous(self, interaction_btn: discord.Interaction, button: discord.ui.Button):
                    nonlocal current_page
                    current_page = (current_page - 1) % len(embeds)
                    await interaction_btn.response.edit_message(embed=embeds[current_page], view=self)

                @discord.ui.button(label="▶️", style=discord.ButtonStyle.secondary)
                async def next(self, interaction_btn: discord.Interaction, button: discord.ui.Button):
                    nonlocal current_page
                    current_page = (current_page + 1) % len(embeds)
                    await interaction_btn.response.edit_message(embed=embeds[current_page], view=self)

                async def on_timeout(self):
                    for item in self.children:
                        item.disabled = True
                    await interaction.edit_original_response(view=self)

            view = Paginator()
            await interaction.response.send_message(embed=embeds[0], view=view)

        except discord.Forbidden:
            await self.send_error(interaction, "I don't have permission to send embeds or use components here.")
        except discord.HTTPException as e:
            await self.send_error(interaction, f"Discord API error occurred: `{e}`")
        except Exception as e:
            await self.send_error(interaction, f"An unexpected error occurred: `{type(e).__name__}` — {e}")


    @app_commands.command(name="museum_edit", description="Edit your museum display cards.")
    @app_commands.describe(
        card1="ID of your first card to display.",
        card2="ID of your second card to display.",
        card3="ID of your third card to display."
    )
    @app_commands.checks.cooldown(1, 15, key=lambda i: i.user.id)  # 15s cooldown
    async def museum_edit(
        self,
        interaction: discord.Interaction,
        card1: Optional[str] = None,
        card2: Optional[str] = None,
        card3: Optional[str] = None
    ):
        try:
            cards = [c for c in (card1, card2, card3) if c]

            if not cards:
                await self.send_error(interaction, "You must specify at least one card ID.")
                return

            if len(cards) > 3:
                await self.send_error(interaction, "You can only display up to **3 cards** in your museum.")
                return

            # Duplicate check
            if len(set(cards)) != len(cards):
                await self.send_error(interaction, "You can’t display the same card more than once.")
                return

            # Example validation: card IDs should be alphanumeric
            for c in cards:
                if not c.isalnum():
                    await self.send_error(interaction, f"Invalid card ID format: `{c}`")
                    return

            # Save display
            self.set_user_museum(interaction.user.id, cards)

            embed = discord.Embed(
                title="✅ Museum Updated",
                description=f"Your museum now displays:\n" + "\n".join(f"- `{c}`" for c in cards),
                colour=discord.Colour.green()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        except app_commands.CommandOnCooldown as e:
            await interaction.response.send_message(
                f"⏳ You're editing too fast! Try again in `{e.retry_after:.1f}` seconds.",
                ephemeral=True
            )
        except discord.Forbidden:
            await self.send_error(interaction, "I don’t have permission to reply with embeds.")
        except discord.HTTPException as e:
            await self.send_error(interaction, f"Discord API error: `{e}`")
        except Exception as e:
            await self.send_error(interaction, f"Unexpected error: `{type(e).__name__}` — {e}")


    @museum_edit.error
    async def museum_edit_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(
                f"⏳ Slow down! Try again in `{error.retry_after:.1f}` seconds.",
                ephemeral=True
            )
        elif isinstance(error, app_commands.MissingPermissions):
            await self.send_error(interaction, "You don’t have permission to use this command.")
        else:
            await self.send_error(interaction, f"Something went wrong: `{error}`")
