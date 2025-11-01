import discord
from discord import app_commands
from discord.ext import commands
import toml

class Flex(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = toml.load("config.toml")["flex"]

    @app_commands.command(name="flex", description="Submit a ball for approval before public flexing.")
    async def flex(self, interaction: discord.Interaction, ball: str):
        mod_channel = self.bot.get_channel(self.config["mod_channel"])
        if not mod_channel:
            return await interaction.response.send_message("Moderator channel not configured.", ephemeral=True)

        embed = discord.Embed(
            title="New Flex Submission",
            description=f"**User:** {interaction.user.mention}\n**Ball:** {ball}",
            color=discord.Color.blurple()
        )

        view = FlexApproval(self.bot, interaction.user, ball, self.config["public_channel"])
        await mod_channel.send(embed=embed, view=view)
        await interaction.response.send_message("Your flex has been sent for approval!", ephemeral=True)

class FlexApproval(discord.ui.View):
    def __init__(self, bot, user, ball, public_channel_id):
        super().__init__(timeout=None)
        self.bot = bot
        self.user = user
        self.ball = ball
        self.public_channel_id = public_channel_id

    @discord.ui.button(label="Approve", style=discord.ButtonStyle.green)
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        public_channel = self.bot.get_channel(self.public_channel_id)
        if not public_channel:
            return await interaction.response.send_message("Public channel not found.", ephemeral=True)
        embed = discord.Embed(
            title="🎉 New Flex!",
            description=f"{self.user.mention} flexed **{self.ball}**!",
            color=discord.Color.gold()
        )
        await public_channel.send(embed=embed)
        await interaction.response.send_message("Flex approved and posted!", ephemeral=True)
        self.stop()

    @discord.ui.button(label="Deny", style=discord.ButtonStyle.red)
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("Flex denied.", ephemeral=True)
        self.stop()

