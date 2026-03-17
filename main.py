import discord
from discord.ext import commands
from discord import app_commands

import config

import db
from datetime import datetime

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

GUILD_ID = discord.Object(id=config.GUILD_ID)


@bot.event
async def on_ready():
    print(f"Login: {bot.user}")

    db.init_db()

    try:
        synced = await bot.tree.sync(guild=GUILD_ID)
        print(f"Sync {len(synced)} commands")
    except Exception as e:
        print(e)


# テスト
@bot.tree.command(name="ping", description="test", guild=GUILD_ID)
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("pong")


# score add
@bot.tree.command(
    name="score_add",
    description="記録追加",
    guild=GUILD_ID
)

@app_commands.describe(
    method="入力方法",
    mode="採点モード",
    song="曲名",
    score="点数"
)

@app_commands.choices(
    method=[
        app_commands.Choice(name="manual", value="manual"),
        app_commands.Choice(name="screenshot", value="screenshot"),
        app_commands.Choice(name="csv", value="csv"),
    ],

    mode=[
        app_commands.Choice(name="DAM AiHeart", value="DAM AiHeart"),
        app_commands.Choice(name="DAM Ai", value="DAM Ai"),
        app_commands.Choice(name="DAM DX-G", value="DAM DX-G"),
        app_commands.Choice(name="DAM DX", value="DAM DX"),

        app_commands.Choice(name="JOYSOUND AI/AI+", value="JOYSOUND AI/AI+"),
        app_commands.Choice(name="JOYSOUND Master", value="JOYSOUND Master"),
        app_commands.Choice(name="JOYSOUND III", value="JOYSOUND III"),

        app_commands.Choice(name="E-bo", value="E-bo"),
        app_commands.Choice(name="Other", value="Other"),
    ]
)

async def score_add(
    interaction: discord.Interaction,
    method: app_commands.Choice[str],
    mode: app_commands.Choice[str],
    song: str,
    score: float,
):

    if method.value != "manual":
        await interaction.response.send_message(
            "manualのみ対応"
        )
        return

    user = interaction.user.name
    date = datetime.now().strftime("%Y-%m-%d")

    db.add_score(
        user,
        song,
        score,
        mode.value,
        date
    )

    await interaction.response.send_message(
        f"保存\n{song}\n{score}\n{mode.value}"
    )


# score list
@bot.tree.command(
    name="score_list",
    description="記録一覧",
    guild=GUILD_ID
)
async def score_list(interaction: discord.Interaction):

    user = interaction.user.name

    rows = db.get_scores(user)

    if not rows:
        await interaction.response.send_message("なし")
        return

    msg = ""

    for i, row in enumerate(rows, start=1):

        id_, song, score, mode, date = row

        msg += f"{i} | {song} | {score} | {mode}\n"

    await interaction.response.send_message(msg)


#score delete
@bot.tree.command(
    name="score_delete",
    description="記録削除",
    guild=GUILD_ID
)
@app_commands.describe(num="表示番号")
async def score_delete(
    interaction: discord.Interaction,
    num: int,
):

    user = interaction.user.name

    rows = db.get_scores(user)

    if num < 1 or num > len(rows):
        await interaction.response.send_message("番号エラー")
        return

    id_, song, score, mode, date = rows[num - 1]

    db.delete_score(id_)

    await interaction.response.send_message(
        f"{song} 削除しました"
    )

bot.run(config.TOKEN)