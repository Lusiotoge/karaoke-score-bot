import discord
from discord.ext import commands
from discord import app_commands

import config
import db

from datetime import datetime

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

GUILD_ID = discord.Object(id=config.GUILD_ID)


MODE_ROLE_MAP = {
    "DAM Ai Heart": 1483501121539670087,
    "DAM Ai": 1483515664080699494,
    "DAM DX-G": 1483515664978415687,
    "DAM DX": 1483515665024552971,

    "JOYSOUND AI/AI+": 1483501157195448380,
    "JOYSOUND Master": 1483515958705262783,
    "JOYSOUND III": 1483515959280009478,

    "E-bo": 1483516271260598282,
}

CHANNEL_MAP = config.CHANNEL_MAP


# ---------------- machine detect ----------------
def get_machine_from_mode(mode: str) -> str:

    mode = mode.lower()

    if "dam" in mode:
        return "DAM"

    if "joysound" in mode:
        return "JOYSOUND"

    return "OTHER"


@bot.event
async def on_ready():

    print(f"Login: {bot.user}")

    db.init_db()

    try:
        synced = await bot.tree.sync(guild=GUILD_ID)
        print(f"Sync {len(synced)} commands")
    except Exception as e:
        print(e)


# ---------------- ping ----------------

@bot.tree.command(
    name="ping",
    description="test",
    guild=GUILD_ID
)
async def ping(interaction: discord.Interaction):

    await interaction.response.send_message("https://media.giphy.com/media/stN3Hes2tPEsPdoWVw/giphy.gif")


# ---------------- score add ----------------

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
    ],

    mode=[
        app_commands.Choice(name="DAM Ai Heart", value="DAM Ai Heart"),
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

    await interaction.response.defer()

    user = interaction.user.name
    date = datetime.now().strftime("%Y-%m-%d")

    last = db.get_last_full(user, song)

    if last:

        last_score, last_mode = last

        if last_score == score and last_mode == mode.value:

            await interaction.followup.send(
                "同じ記録のため保存しません"
            )

            return

    db.add_score(
        user,
        song,
        score,
        mode.value,
        date
    )

    role_id = MODE_ROLE_MAP.get(mode.value)

    if role_id:
        role_mention = f"<@&{role_id}>"
    else:
        role_mention = mode.value


    # ←これを先に送る（interaction応答）

    machine = get_machine_from_mode(mode.value)

    color = get_role_color(
        interaction.guild,
        machine
    )

    embed = discord.Embed(
        title=song,
        description=f"ユーザー：{interaction.user.name}",
        color=color
    )

    embed.set_thumbnail(
        url=interaction.user.display_avatar.url
    )

    embed.add_field(
        name="今回の点数",
        value=score,
        inline=False
    )

    embed.add_field(
        name="採点モード",
        value=mode.value,
        inline=False
    )

    embed.add_field(
        name="ロール",
        value=role_mention,
        inline=False
    )

    embed.set_footer(
        text="記録を保存しました"
    )


    # interaction返信

    await interaction.followup.send(
        embed=embed
    )


    # チャンネル分け

    channel_id = CHANNEL_MAP.get(machine)

    if channel_id:

        channel = interaction.guild.get_channel(channel_id)

        if channel:

            await channel.send(
                embed=embed
            )

# ---------------- list ----------------

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


# ---------------- delete ----------------

@bot.tree.command(
    name="score_delete",
    description="記録削除",
    guild=GUILD_ID
)

@app_commands.describe(num="番号")

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


# ---------------- best ----------------

@bot.tree.command(
    name="score_best",
    description="曲別最高点",
    guild=GUILD_ID
)
async def score_best(interaction: discord.Interaction):

    user = interaction.user.name

    rows = db.get_best_scores(user)

    if not rows:
        await interaction.response.send_message("なし")
        return

    msg = "最高点\n"

    for song, score in rows:
        msg += f"{song} {score}\n"

    await interaction.response.send_message(msg)


# ---------------- song info ----------------

@bot.tree.command(
    name="song_info",
    description="曲情報",
    guild=GUILD_ID
)

@app_commands.describe(song="曲名")

async def song_info(
    interaction: discord.Interaction,
    song: str,
):

    await interaction.response.defer()

    user = interaction.user.name

    last, best = db.get_song_stats(user, song)

    if not last:
        await interaction.response.send_message("データなし")
        return

    last_score, last_mode, last_date = last
    best_score, best_mode, best_date = best

    # ロールメンション取得

    last_role_id = MODE_ROLE_MAP.get(last_mode)
    best_role_id = MODE_ROLE_MAP.get(best_mode)

    if last_role_id:
        last_mode_text = f"<@&{last_role_id}>"
    else:
        last_mode_text = last_mode

    if best_role_id:
        best_mode_text = f"<@&{best_role_id}>"
    else:
        best_mode_text = best_mode

    # 機種判定

    if last_mode and "DAM" in last_mode:
        machine = "DAM"
    elif last_mode and "JOY" in last_mode:
        machine = "JOYSOUND"
    else:
        machine = "OTHER"

    color = get_role_color(
        interaction.guild,
        machine
    )

    embed = discord.Embed(
        title=song,
        color=color
    )

    embed.set_thumbnail(
        url=interaction.user.display_avatar.url
    )

    embed.add_field(
        name="機種",
        value=machine,
        inline=False
    )

    embed.add_field(
        name="最新記録",
        value=f"{last_score}\n{last_mode_text}\n{last_date}",
        inline=False
    )

    embed.add_field(
        name="過去最高点",
        value=f"{best_score}\n{best_mode_text}\n{best_date}",
        inline=False
    )

    await interaction.followup.send(
        embed=embed
    )


# ---------------- role color ----------------

def get_role_color(guild, role_name):

    role = discord.utils.get(
        guild.roles,
        name=role_name
    )

    if role:
        return role.color

    return discord.Color.light_grey()


bot.run(config.TOKEN)