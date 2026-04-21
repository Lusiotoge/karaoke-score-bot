import discord
from discord import app_commands
import db

class RankingCommands(app_commands.Group):
    def __init__(self):
        super().__init__(name="ranking", description="ランキング")

    @app_commands.command(name="top", description="全体ランキング")
    async def top(self, interaction: discord.Interaction):

        rows = db.get_all_scores()

        if not rows:
            await interaction.response.send_message("データなし")
            return

        desc = ""

        for i, (user, score) in enumerate(rows[:10], 1):
            desc += f"{i}. {user} - {score}\n"

        embed = discord.Embed(
            title="🏆 ランキング",
            description=desc,
            color=discord.Color.gold()
        )

        await interaction.response.send_message(embed=embed)