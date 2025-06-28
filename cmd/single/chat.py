import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional

class ChatCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="chat", description="Send message to specified channel.")
    @app_commands.describe(
        message="Message content.",
        channel="Channel to send message",
        reply="Message ID to reply to"
    )
    async def chat(self, interaction: discord.Interaction, message: str, channel: discord.TextChannel, reply: Optional[str] = None):
        if interaction.guild is not None:
            bot_member = interaction.guild.me
            if not channel.permissions_for(bot_member).send_messages:
                await interaction.response.send_message("❌ I **do not have permission** to send messages in this channel.", ephemeral=True)
                return

        if interaction.guild is not None and interaction.channel is not None:
            author = interaction.user
            if not isinstance(author, discord.Member):
                author = interaction.guild.get_member(author.id)
            if not author or not interaction.channel.permissions_for(author).manage_channels:
                await interaction.response.send_message("⚠️ You need the `Manage Channels` permission to use this command.", ephemeral=True)
                return

        if interaction.guild is not None:
            if (
                "@everyone" in message or
                "@here" in message or
                any(f"<@{member.id}>" in message for member in interaction.guild.members) or
                any(f"<@!{member.id}>" in message for member in interaction.guild.members) or
                any(f"<@&{role.id}>" in message for role in interaction.guild.roles)
            ):
                await interaction.response.send_message("❌ Mentions are not allowed in the message.", ephemeral=True)
                return
        else:
            if "@everyone" in message or "@here" in message:
                await interaction.response.send_message("❌ Mentions are not allowed in the message.", ephemeral=True)
                return

        ref_msg = None
        if reply is not None:
            try:
                message_id = int(reply)
            except ValueError:
                await interaction.response.send_message("❌ Invalid message ID, please enter a number.", ephemeral=True)
                return

            try:
                ref_msg = await channel.fetch_message(message_id)
            except discord.NotFound:
                await interaction.response.send_message("❌ The message ID must be valid for the channel.", ephemeral=True)
                return
            except discord.Forbidden:
                await interaction.response.send_message("❌ I **do not have permission** to send messages in this channel.", ephemeral=True)
                return
            except Exception:
                await interaction.response.send_message("❌ The message ID must be valid for the channel.", ephemeral=True)
                return

        try:
            if ref_msg is not None:
                await channel.send(content=message, reference=ref_msg)
            else:
                await channel.send(content=message)
            await interaction.response.send_message("✅ Message has been sent!", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ I **do not have permission** to send messages in this channel.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error sending message: {e}", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(ChatCog(bot))
