import discord
from discord.ext import commands
from discord import app_commands

import config
import db

import csv
import io

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

def get_score_style(score):

    if score == 100:
        return 0xFFD700, "👑"

    if score >= 95:
        return 0x9B59B6, "🟣"

    if score >= 90:
        return 0x3498DB, "🔵"

    if score >= 80:
        return 0x2ECC71, "🟢"

    return 0x95A5A6, "⚪"


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
    machine="機種",
    mode="採点モード",
    song="曲名",
    score="点数"
)

@app_commands.choices(

    method=[
        app_commands.Choice(name="manual", value="manual"),
        app_commands.Choice(name="csv", value="csv"),
    ],

    machine=[
        app_commands.Choice(name="DAM", value="DAM"),
        app_commands.Choice(name="JOYSOUND", value="JOYSOUND"),
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
    machine: app_commands.Choice[str] | None = None,
    mode: app_commands.Choice[str] | None = None,
    song: str | None = None,
    score: float | None = None,
    file: discord.Attachment | None = None,
):

    await interaction.response.defer()

    # =========================
    # manualチェック
    # =========================

    if method.value == "manual":

        if not song or not score or not mode:

            await interaction.followup.send(
                "manualでは曲名・点数・モードが必要です",
                ephemeral=True
            )
            return


    # =========================
    # csvチェック
    # =========================

    if method.value == "csv":

        if not file:

            await interaction.followup.send(
                "CSVファイルを添付してください",
                ephemeral=True
            )
            return

        if not machine:

            await interaction.followup.send(
                "CSVでは機種を選択してください",
                ephemeral=True
            )
            return

        if not mode:

            await interaction.followup.send(
                "採点モードを選択してください",
                ephemeral=True
            )
            return

        data = await file.read()
        text = data.decode("utf-8")
        f = io.StringIO(text)
        reader = csv.reader(f)

        updated = []
        new = []

        user = interaction.user.name
        date = datetime.now().strftime("%Y-%m-%d")

        for i, row in enumerate(reader):

            if i == 0:
                continue

            try:

                song = row[2].strip()

                score_text = row[4].strip()

                if not score_text:
                    continue

                score = float(score_text)

                machine_name = machine.value
                mode_name = mode.value

                last = db.get_last_full(user, song)

                if last:

                    last_score, last_mode = last

                    if score > last_score:

                        db.add_score(
                            user,
                            song,
                            score,
                            mode_name,
                            date
                        )

                        updated.append(
                            f"[{machine_name}] {song} {last_score} → {score}"
                        )

                else:

                    db.add_score(
                        user,
                        song,
                        score,
                        mode_name,
                        date
                    )

                    new.append(
                        f"[{machine_name}] {song} {score}"
                    )

            except Exception as e:
                print("CSV error:", row, e)

    # ===== 通知 =====

    if not updated and not new:

        await interaction.followup.send(
            "更新なし",
            ephemeral=True
        )
        return

    embed = discord.Embed(
        title="CSV登録結果",
        color=discord.Color.blue()
    )

    if updated:

        embed.add_field(
            name="更新",
            value="\n".join(updated[:20]),
            inline=False
        )

    if new:

        embed.add_field(
            name="新規",
            value="\n".join(new[:20]),
            inline=False
        )

    await interaction.followup.send(
        embed=embed
    )

    return

    user = interaction.user.name
    date = datetime.now().strftime("%Y-%m-%d")

    last = db.get_last_full(user, song)

    last = db.get_last_full(user, song)

    improved = False

    if last:

        last_score, last_mode = last

        # 同じ記録 → 保存しない
        if last_score == score and last_mode == mode.value:

            await interaction.followup.send(
                "同じ記録のため保存しません"
            )
            return

        # 上昇したか判定
        if score > last_score:
            improved = True

    else:
        # 初回は更新扱い
        improved = True


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

    # ←ここ変更（mode → machine）
    embed.add_field(
        name="機種",
        value=machine,
        inline=False
    )

    # ←ここ変更（role表示）
    embed.add_field(
        name="採点",
        value=role_mention,
        inline=False
    )

    embed.set_footer(
        text="記録を保存しました"
    )

    first_time = False
    score_diff = 0

    if last:
        last_score, last_mode = last

        if last_score == score and last_mode == mode.value:
            await interaction.followup.send("同じ記録のため保存しません")
            return

        if score > last_score:
            improved = True
            score_diff = score - last_score
        else:
            improved = False
    else:
        improved = True
        first_time = True

    db.add_score(user, song, score, mode.value, date)

    # ここから差分通知部分
    if improved and not first_time:
        # 公開通知（チャンネル）
        channel_id = CHANNEL_MAP.get(machine)
        if channel_id:
            channel = interaction.guild.get_channel(channel_id)
            if channel:
                await channel.send(f"**{user}** さんがスコアを更新しました！ (+{score_diff:.3f})")
                await channel.send(embed=embed)

    # 自分への返信
        await interaction.followup.send(
            content=f"更新しました (+{score_diff:.3f})",
            embed=embed
         )
    else:
    # 初回登録 or 前回スコアより低い場合は自分だけに通知
        await interaction.followup.send(
            content="記録しました",
            embed=embed,
            ephemeral=True
        )


# ---------------- list ----------------
# ① まず普通の関数（デコレーターなし）
def create_score_embed(rows, page, guild, per_page=20):
    start = page * per_page
    end = start + per_page
    view_rows = rows[start:end]

    embed = discord.Embed(
        title="スコア一覧",
        color=discord.Color.blue()
    )

    description = ""

    for i, row in enumerate(view_rows, start=start+1):
        id_, song, score, mode, date = row

        # ロール取得
        role = discord.utils.get(guild.roles, name=mode)
        role_mention = role.mention if role else mode

        # ⭐評価
        if score >= 90:
            mark = "🌟"
        elif score >= 85:
            mark = "⭐"
        else:
            mark = ""

        # 👇 2行表示
        description += f"{i:02d}. {song} {mark}\n　└ {score}点 / {role_mention}\n"

    embed.description = description

    total_pages = (len(rows) - 1) // per_page + 1
    embed.set_footer(text=f"{page+1}/{total_pages}ページ")

    return embed

# ② 次にView
class ScoreListView(discord.ui.View):
    def __init__(self, rows, guild):
        super().__init__(timeout=180)
        self.original_rows = rows  # 元データ保存
        self.rows = rows.copy()
        self.guild = guild
        self.page = 0
        self.per_page = 20
        self.sort_mode = "default"

    def sort_rows(self):
        if self.sort_mode == "score":
            self.rows = sorted(self.original_rows, key=lambda x: x[2], reverse=True)
        elif self.sort_mode == "song":
            self.rows = sorted(self.original_rows, key=lambda x: x[1])
        elif self.sort_mode == "date":
            self.rows = sorted(self.original_rows, key=lambda x: x[4], reverse=True)
        else:
            self.rows = self.original_rows.copy()

    async def update(self, interaction):
        self.sort_rows()
        embed = create_score_embed(self.rows, self.page, self.guild, self.per_page)
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary, row=0)
    async def prev(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1
        await self.update(interaction)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary, row=0)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        max_page = (len(self.rows) - 1) // self.per_page
        if self.page < max_page:
            self.page += 1
        await self.update(interaction)

    @discord.ui.button(label="点数順", style=discord.ButtonStyle.primary)
    async def sort_score(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.sort_mode = "score"
        self.page = 0
        await self.update(interaction)

    @discord.ui.button(label="曲名順", style=discord.ButtonStyle.primary)
    async def sort_song(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.sort_mode = "song"
        self.page = 0
        await self.update(interaction)

    @discord.ui.button(label="日付順", style=discord.ButtonStyle.primary)
    async def sort_date(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.sort_mode = "date"
        self.page = 0
        await self.update(interaction)

# ③ 最後にコマンド（ここにデコレーター！）
@bot.tree.command(
    name="score_list",
    description="記録一覧",
    guild=GUILD_ID
)
async def score_list(interaction: discord.Interaction):

    await interaction.response.defer()  # ← 追加

    user = interaction.user.name
    rows = db.get_scores(user)

    if not rows:
        await interaction.followup.send("記録なし")
        return

    view = ScoreListView(rows, interaction.guild)
    embed = create_score_embed(rows, 0, interaction.guild)

    await interaction.followup.send(  # ← 変更
        embed=embed,
        view=view
    )


# ---------------- delete ----------------

class DeleteConfirmView(discord.ui.View):

    def __init__(self, user_id):
        super().__init__(timeout=30)
        self.user_id = user_id


    async def interaction_check(self, interaction):

        if interaction.user.id != self.user_id:

            await interaction.response.send_message(
                "この操作は実行できません",
                ephemeral=True
            )

            return False

        return True


    @discord.ui.button(
        label="削除",
        style=discord.ButtonStyle.danger
    )
    async def delete_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        user = interaction.user.name

        db.delete_by_user(user)

        await interaction.response.edit_message(
            content="削除しました",
            view=None
        )


    @discord.ui.button(
        label="キャンセル",
        style=discord.ButtonStyle.secondary
    )
    async def cancel_button(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):

        await interaction.response.edit_message(
            content="キャンセルしました",
            view=None
        )

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

@bot.tree.command(
    name="score_delete_me",
    description="⚠この操作を行うとあなたのこれまでの記録が全て消えます！",
    guild=GUILD_ID
)
async def score_delete_me(
    interaction: discord.Interaction,
):

    view = DeleteConfirmView(
        interaction.user.id
    )

    await interaction.response.send_message(
        "⚠本当に削除しますか？",
        view=view,
        ephemeral=True
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