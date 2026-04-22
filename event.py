import discord
from discord.ext import tasks
import random
import db
import os


class EventSystem:
    def __init__(self, bot):
        self.bot = bot

        if not self.monthly_task.is_running():
            self.monthly_task.start()

    @tasks.loop(minutes=5)
    async def monthly_task(self):

        now = discord.utils.utcnow()

        if not (now.day == 1 and now.hour == 0 and now.minute < 5):
            return

        GUILD_ID = int(os.environ["GUILD_ID"])
        EVENT_CHANNEL_ID = int(os.environ["EVENT_CHANNEL_ID"])

        guild = self.bot.get_guild(GUILD_ID)
        if not guild:
            return

        channel = guild.get_channel(EVENT_CHANNEL_ID)
        if not channel:
            return

        songs = db.get_all_songs()
        if not songs:
            return

        last_song = db.get_monthly_song()

        candidates = [s for s in songs if s != last_song] or songs
        song = random.choice(candidates)

        db.set_monthly_song(song)

        embed = discord.Embed(
            title="🎯 今月の課題曲",
            description=song,
            color=discord.Color.gold()
        )

        await channel.send(embed=embed)

    @monthly_task.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()


from discord import app_commands


class EventCommands(app_commands.Group):
    def __init__(self):
        super().__init__(name="event", description="イベント")

    @app_commands.command(name="ranking", description="課題曲ランキング")
    async def ranking(self, interaction: discord.Interaction):

        song = db.get_monthly_song()
        if not song:
            await interaction.response.send_message("課題曲なし")
            return

        rows = db.get_monthly_ranking(song)

        if not rows:
            await interaction.response.send_message("まだデータなし")
            return

        desc = ""
        for i, (user, score) in enumerate(rows[:10], 1):
            desc += f"{i}. {user} - {score}\n"

        embed = discord.Embed(
            title=f"🎯 課題曲ランキング\n{song}",
            description=desc,
            color=discord.Color.orange()
        )

        await interaction.response.send_message(embed=embed)