import discord
from discord.ext import commands
from discord import app_commands

class ChatCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="chat", description="Send message to specified channel.")
    @app_commands.describe(
        message="Message content.",
        channel="Channel to send message",
        reply="Message ID to reply to"
    )
    async def chat(self, interaction: discord.Interaction, message: str, channel: discord.TextChannel, reply: str = None):
        if interaction.guild is not None:
            bot_member = interaction.guild.me
            if not channel.permissions_for(bot_member).send_messages:
                await interaction.response.send_message("Tôi **không có quyền hạn** gửi tin nhắn vào channel", ephemeral=True)
                return

        ref_msg = None
        if reply is not None:
            try:
                message_id = int(reply)
            except ValueError:
                await interaction.response.send_message("ID tin nhắn không hợp lệ, vui lòng nhập số.", ephemeral=True)
                return

            try:
                ref_msg = await channel.fetch_message(message_id)
            except discord.NotFound:
                await interaction.response.send_message("ID message phải hợp lệ với channel", ephemeral=True)
                return
            except discord.Forbidden:
                await interaction.response.send_message("Tôi **không có quyền hạn** gửi tin nhắn vào kênh", ephemeral=True)
                return
            except Exception:
                await interaction.response.send_message("ID message phải hợp lệ với channel", ephemeral=True)
                return

        try:
            await channel.send(content=message, reference=ref_msg)
            await interaction.response.send_message("Tin nhắn đã được gửi!", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("Tôi **không có quyền hạn** gửi tin nhắn vào kênh", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Lỗi khi gửi tin nhắn: {e}", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(ChatCog(bot))
