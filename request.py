import discord
from discord import app_commands
from datetime import datetime
import os


class RequestActionView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def update_embed(self, interaction, new_status: str):
        embed = interaction.message.embeds[0]

        for i, field in enumerate(embed.fields):
            if field.name == "状態":
                embed.set_field_at(i, name="状態", value=new_status, inline=False)

        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="✅ 完了", style=discord.ButtonStyle.success)
    async def done(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_embed(interaction, "完了")

    @discord.ui.button(label="❌ 辞退", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_embed(interaction, "辞退")

    @discord.ui.button(label="🔄 未対応に戻す", style=discord.ButtonStyle.secondary)
    async def reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_embed(interaction, "未対応")


class RequestCommands(app_commands.Group):
    def __init__(self):
        super().__init__(name="request", description="リクエスト関連")

    @app_commands.command(name="send", description="楽曲リクエストを送信")
    async def send(
        self,
        interaction: discord.Interaction,
        song: str,
        url: str,
        user: discord.Member | None = None,
        here: bool = False,
    ):
        REQUEST_CHANNEL_ID = int(os.environ["REQUEST_CHANNEL_ID"])
        channel = interaction.guild.get_channel(REQUEST_CHANNEL_ID)

        if not channel:
            await interaction.response.send_message("チャンネルが見つかりません", ephemeral=True)
            return

        # 宛先
        if user:
            target_text = user.mention
            target_id = str(user.id)
        elif here:
            target_text = "@here"
            target_id = "here"
        else:
            await interaction.response.send_message("userかhereを指定してください", ephemeral=True)
            return

        embed = discord.Embed(
            title="📩 リクエスト",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )

        embed.add_field(name="送信者", value=interaction.user.mention, inline=False)
        embed.add_field(name="宛先", value=target_text, inline=False)
        embed.add_field(name="曲名", value=song, inline=False)
        embed.add_field(name="URL", value=url, inline=False)
        embed.add_field(name="状態", value="未対応", inline=False)

        embed.set_footer(text=f"target:{target_id}")

        await channel.send(
            content=target_text,
            embed=embed,
            view=RequestActionView()
        )

        await interaction.response.send_message("送信しました", ephemeral=True)

    @app_commands.command(name="list", description="自分宛リクエスト確認")
    async def list(self, interaction: discord.Interaction):

        REQUEST_CHANNEL_ID = int(os.environ["REQUEST_CHANNEL_ID"])
        channel = interaction.guild.get_channel(REQUEST_CHANNEL_ID)

        user_id = str(interaction.user.id)

        results = []

        async for msg in channel.history(limit=50):
            if not msg.embeds:
                continue

            e = msg.embeds[0]

            if not e.footer or not e.footer.text:
                continue

            if f"target:{user_id}" in e.footer.text or "target:here" in e.footer.text:
                results.append((msg, e))

        if not results:
            await interaction.response.send_message("リクエストなし", ephemeral=True)
            return

        await interaction.response.send_message(f"{len(results)}件見つかりました", ephemeral=True)

        for msg, e in results[:5]:
            await interaction.followup.send(embed=e, view=RequestActionView(), ephemeral=True)