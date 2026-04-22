import discord                                              
from discord.ext import commands
from discord import app_commands
from request import RequestCommands

from ranking import RankingCommands

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

from event import EventSystem, EventCommands

import db

import csv
import io

from datetime import datetime

import os

TOKEN = os.environ["TOKEN"]
GUILD_ID = int(os.environ["GUILD_ID"])

from flask import Flask
import threading

app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is alive!"

def run_web():
    app.run(host="0.0.0.0", port=10000)

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

CHANNEL_MAP = {
    "DAM": 1484167905993162844,
    "JOYSOUND": 1484167951971123222,
    "Other": 1484168288572543146,
}

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


def parse_joysound_result(image_path):
    return []

def create_ocr_embed(results):
    embed = discord.Embed(
        title="OCR結果確認",
        color=discord.Color.orange()
    )

    desc = ""
    for i, r in enumerate(results, 1):
        desc += f"{i}. {r['song']} / {r['score']} / {r['mode']}\n"

    embed.description = desc
    embed.set_footer(text="問題なければ登録、違う場合は修正してください")

    return embed

class OCRConfirmView(discord.ui.View):
    def __init__(self, results, user):
        super().__init__(timeout=180)
        self.results = results
        self.user = user

    @discord.ui.button(label="登録", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):

        for r in self.results:
            db.add_score(
                user=self.user,
                song=r["song"],
                score=r["score"],
                mode=r["mode"]
            )

        await interaction.response.edit_message(
            content="登録完了しました",
            embed=None,
            view=None
        )

    @discord.ui.button(label="修正", style=discord.ButtonStyle.secondary)
    async def edit(self, interaction: discord.Interaction, button: discord.ui.Button):

        await interaction.response.send_message(
            "修正は /score_edit コマンドで行ってください",
            ephemeral=True
        )

@bot.tree.command(
    name="ocr_import",
    description="画像からスコア読み込み",
    guild=discord.Object(id=GUILD_ID)
)

async def ocr_import(interaction: discord.Interaction, image: discord.Attachment):

    file_path = f"temp_{interaction.user.id}.png"
    await image.save(file_path)

    results = parse_joysound_result(file_path)

    if not results:
        await interaction.response.send_message("読み取り失敗")
        return

    embed = create_ocr_embed(results)
    view = OCRConfirmView(results, interaction.user.name)

    await interaction.response.send_message(
        embed=embed,
        view=view
    )


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

    guild = discord.Object(id=GUILD_ID)

    try:
        # コマンド追加
        bot.tree.add_command(RequestCommands(), guild=guild)
        bot.tree.add_command(RankingCommands(), guild=guild)
        bot.tree.add_command(EventCommands(), guild=guild)

        # 同期
        synced = await bot.tree.sync(guild=guild)
        print(f"Sync {len(synced)} commands")

    except Exception as e:
        print(e)

    # イベント初期化
    EventSystem(bot)

# ---------------- ping ----------------

@bot.tree.command(
    name="ping",
    description="test",
    guild=discord.Object(id=GUILD_ID)
)
async def ping(interaction: discord.Interaction):

    await interaction.response.send_message("https://media.giphy.com/media/stN3Hes2tPEsPdoWVw/giphy.gif")


# ---------------- score add ----------------
@bot.tree.command(
    name="score_add",
    description="記録追加",
    guild=discord.Object(id=GUILD_ID)
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
        app_commands.Choice(name="csv_template", value="csv_template"),
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

    user = interaction.user.name
    date = datetime.now().strftime("%Y-%m-%d")

    # =========================
    # manual
    # =========================
    if method.value == "manual":

        if not song or not score or not mode:
            await interaction.followup.send(
                "manualでは曲名・点数・モードが必要です",
                ephemeral=True
            )
            return

        last = db.get_last_full(user, song)

        score_diff = 0
        improved = False
        first_time = False

        if last:
            last_score, _ = last
            if score > last_score:
                improved = True
                score_diff = score - last_score
        else:
            improved = True
            first_time = True

        db.add_score(user, song, score, mode.value, date)

        if first_time:
            msg = "🎉 初回登録！"
        elif improved:
            msg = f"✨ スコア更新！ (+{score_diff:.3f})"
        else:
            msg = "記録しました（更新なし）"

        await interaction.followup.send(msg, ephemeral=True)
        return

    # =========================
    # csv
    # =========================
    elif method.value == "csv":

        if not file or not machine or not mode:
            await interaction.followup.send(
                "CSVはファイル・機種・モード必須",
                ephemeral=True
            )
            return

        data = await file.read()
        text = data.decode("utf-8")
        reader = csv.reader(io.StringIO(text))

        updated = 0
        new = 0

        for i, row in enumerate(reader):
            if i == 0:
                continue

            if len(row) < 5:
                continue

            try:
                song = row[2].strip()
                score_text = row[4].strip()
                if not score_text:
                    continue

                score = float(score_text)

                last = db.get_last_full(user, song)

                if last:
                    if score > last[0]:
                        db.add_score(user, song, score, mode.value, date)
                        updated += 1
                else:
                    db.add_score(user, song, score, mode.value, date)
                    new += 1

            except Exception as e:
                print("CSV error:", row, e)

        await interaction.followup.send(
            f"更新:{updated}件 / 新規:{new}件",
            ephemeral=True
        )
        return

    # =========================
    # csv_template
    # =========================
    elif method.value == "csv_template":

        if not file:
            await interaction.followup.send(
                "CSVファイルを添付してください",
                ephemeral=True
            )
            return

        data = await file.read()
        text = data.decode("utf-8")
        reader = csv.reader(io.StringIO(text))

        updated = 0
        new = 0

        for i, row in enumerate(reader):
            if i < 2:
                continue

            if len(row) < 5:  # ←修正済み
                continue

            try:
                song = row[0].strip()
                score_text = row[4].strip()
                if not score_text:
                    continue

                score = float(score_text)
                mode_name = row[3].strip()

                last = db.get_last_full(user, song)

                if last:
                    if score > last[0]:
                        db.add_score(user, song, score, mode_name, date)
                        updated += 1
                else:
                    db.add_score(user, song, score, mode_name, date)
                    new += 1

            except:
                continue

        await interaction.followup.send(
            f"更新:{updated}件 / 新規:{new}件",
            ephemeral=True
        )
        return


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

@bot.tree.command(
    name="score_list",
    description="記録一覧",
    guild=discord.Object(id=GUILD_ID)
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
    guild=discord.Object(id=GUILD_ID)
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
    guild=discord.Object(id=GUILD_ID)
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
    guild=discord.Object(id=GUILD_ID)
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
    guild=discord.Object(id=GUILD_ID)
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


# ---------------- CSV Template link ----------------
@bot.tree.command(
    name="template",
    description="CSVテンプレートを取得",
    guild=discord.Object(id=GUILD_ID)
)
async def template(interaction: discord.Interaction):

    url = "https://docs.google.com/spreadsheets/d/1l141WQBHxCHvBKv9Tde3DZA9ihyGtoIb_KHxU3py0WY/copy"

    await interaction.response.send_message(
        f"テンプレートはこちら👇 リンク先からコピーして自分のドライブに入れて使ってください\n{url}",
        ephemeral=True
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

threading.Thread(target=run_web, daemon=True).start()

bot.run(TOKEN)