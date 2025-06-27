import discord
from discord import app_commands
from discord.ext import commands
import yt_dlp as youtube_dl
import asyncio
import time
import random
import io
import tempfile
import os
from discord.http import Route

class Replay(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.platform_config = {
            'tiktok.com': {
                'referer': 'https://www.tiktok.com/',
                'origin': 'https://www.tiktok.com',
                'headers': {
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'en-US,en;q=0.9',
                    'Sec-Fetch-Mode': 'navigate',
                }
            },
            'youtube.com/shorts': {
                'referer': 'https://www.youtube.com/',
                'origin': 'https://www.youtube.com',
                'headers': {
                    'Accept': '*/*',
                    'Sec-Fetch-Mode': 'no-cors',
                    'Accept-Language': 'en-US,en;q=0.5'
                }
            }
        }
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3.1 Mobile/15E148 Safari/604.1"
        ]
    
    def get_platform_config(self, url: str) -> dict:
        for platform, config in self.platform_config.items():
            if platform in url.lower():
                return config
        return {}
    
    async def download_video(self, url: str) -> tuple:
        platform_config = self.get_platform_config(url)
        user_agent = random.choice(self.user_agents)
        
        temp_fd, temp_path = tempfile.mkstemp(suffix=".mp4")
        os.close(temp_fd)
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio/best[ext=mp4]/best',
            'quiet': True,
            'verbose': False,
            'no_warnings': True,
            'ignoreerrors': False,
            'nocheckcertificate': True,
            'force_overwrites': True,
            'cookiefile': 'cookies.txt',
            'http_headers': {
                'User-Agent': user_agent,
                'Referer': platform_config.get('referer', 'https://www.google.com/'),
                'Origin': platform_config.get('origin', ''),
                **platform_config.get('headers', {})
            },
            'force-ipv4': True,
            'outtmpl': temp_path,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android'],
                    'skip': ['hls', 'dash']
                }
            },
            'recodevideo': 'mp4',
            'postprocessor_args': ['-c:v', 'libx264', '-profile:v', 'main', '-preset', 'medium', '-crf', '23']
        }
        
        try:
            with youtube_dl.YoutubeDL(ydl_opts) as ydl:
                loop = asyncio.get_event_loop()
                data = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=True))
                if data and isinstance(data, dict) and 'entries' in data and data['entries']:
                    data = data['entries'][0]
        except Exception as e:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise Exception(f"Download failed: {str(e)}")
        
        try:
            with open(temp_path, 'rb') as f:
                video_bytes = f.read()
            if len(video_bytes) == 0:
                raise Exception("Downloaded file is empty (0 bytes)")
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
        return video_bytes, data

    async def suppress_embeds_via_patch(self, interaction: discord.Interaction, message_id: int):
        route = Route(
            "PATCH",
            f"/webhooks/{interaction.application_id}/{interaction.token}/messages/{message_id}"
        )
        payload = {"flags": 4}
        await self.bot.http.request(route, json=payload)

    @app_commands.command(
        name="replay",
        description="Replay video from TikTok & YouTube Shorts."
    )
    async def replay(self, interaction: discord.Interaction, video_url: str):
        SUPPORTED_PLATFORMS = ["tiktok.com", "youtube.com/shorts"]
        if not any(p in video_url.lower() for p in SUPPORTED_PLATFORMS):
            return await interaction.response.send_message(
                "⚠️ Only TikTok and YouTube Shorts are supported!",
                ephemeral=True
            )
    
        await interaction.response.defer()
    
        try:
            video_bytes, info = await self.download_video(video_url)
        except Exception as e:
            return await interaction.followup.send(
                f"⚠️ Video download error: ```{str(e)}```",
                ephemeral=True
            )
    
        if len(video_bytes) > 25 * 1024 * 1024:
            return await interaction.followup.send(
                "⚠️ Video exceeds 25MB!",
                ephemeral=True
            )
    
        timestamp_val = None
        upload_date = info.get('upload_date') or info.get('release_date')
        if upload_date:
            try:
                struct_time = time.strptime(upload_date, "%Y%m%d")
                timestamp_val = int(time.mktime(struct_time)) - (7 * 3600)
            except Exception:
                timestamp_val = None
        if not timestamp_val and info.get('timestamp'):
            try:
                timestamp_val = int(info['timestamp'])
            except Exception:
                timestamp_val = None
        if timestamp_val:
            time_str = f"<t:{timestamp_val}:R>"
        else:
            time_str = "N/A"
    
        video_title = info.get('title', 'Video replay')
        video_link = info.get('webpage_url', video_url)
        message_content = (
            f"{video_title} (Uploaded: {time_str})\n"
            f"-# [↪ Original link]({video_link})"
        )
    
        filename = f"replay_{info['id']}.mp4"
        file = discord.File(io.BytesIO(video_bytes), filename=filename)
    
        sent_message = await interaction.followup.send(
            content=message_content,
            file=file,
            wait=True
        )
        await self.suppress_embeds_via_patch(interaction, sent_message.id)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        SUPPORTED_PLATFORMS = ["tiktok.com", "youtube.com/shorts"]
        found_url = None
        for word in message.content.split():
            for platform in SUPPORTED_PLATFORMS:
                if platform in word.lower():
                    found_url = word
                    break
            if found_url:
                break
        if not found_url:
            return
        try:
            await message.edit(suppress=True)
        except Exception:
            pass
        try:
            await message.channel.typing()
            video_bytes, info = await self.download_video(found_url)
        except Exception as e:
            await message.channel.send(f"⚠️ Video download error: ```{str(e)}```")
            return
        if len(video_bytes) > 25 * 1024 * 1024:
            await message.channel.send("⚠️ Video exceeds 25MB!")
            return
        timestamp_val = None
        upload_date = info.get('upload_date') or info.get('release_date')
        if upload_date:
            try:
                struct_time = time.strptime(upload_date, "%Y%m%d")
                timestamp_val = int(time.mktime(struct_time)) - (7 * 3600)
            except Exception:
                timestamp_val = None
        if not timestamp_val and info.get('timestamp'):
            try:
                timestamp_val = int(info['timestamp'])
            except Exception:
                timestamp_val = None
        if timestamp_val:
            time_str = f"<t:{timestamp_val}:R>"
        else:
            time_str = "N/A"
        video_title = info.get('title', 'Video replay')
        video_link = info.get('webpage_url', found_url)
        message_content = (
            f"{video_title} (Uploaded: {time_str})\n"
            f"-# [↪ Original link]({video_link})"
        )
        filename = f"replay_{info['id']}.mp4"
        file = discord.File(io.BytesIO(video_bytes), filename=filename)
        sent_message = await message.channel.send(content=message_content, file=file)
        try:
            await sent_message.edit(suppress=True)
        except Exception:
            try:
                route = Route(
                    "PATCH",
                    f"/channels/{sent_message.channel.id}/messages/{sent_message.id}"
                )
                payload = {"flags": 4}
                await self.bot.http.request(route, json=payload)
            except Exception:
                pass

async def setup(bot: commands.Bot):
    await bot.add_cog(Replay(bot))
