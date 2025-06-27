import discord
from discord.ext import commands
import psutil # type: ignore

class About(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='about')
    async def show_info(self, ctx, footer_image_url: str = "https://i.imgur.com/nnzDSnZ.png"):
        embed = discord.Embed(title="About Me", description="Enou là bot thuộc thể loại economy, minigame được phát triển độc lập bởi <@880694639227699290>. Bot mang sứ mệnh sẽ tạo ra một sân chơi giải trí cho mọi người trên Discord.", color=0x00ff00)
        embed.add_field(name="Total server", value=f"{len(self.bot.guilds)}", inline=True)
        embed.add_field(name="Total members", value=f"{sum(len(guild.members) for guild in self.bot.guilds)}", inline=True)
        embed.add_field(name="Total channels", value=f"{sum(len(guild.channels) for guild in self.bot.guilds)}", inline=True)
        embed.add_field(name="Text & voice channels", value=f"Text: {sum(len(guild.text_channels) for guild in self.bot.guilds)}, Voice: {sum(len(guild.voice_channels) for guild in self.bot.guilds)}", inline=True)
        cpu_usage = psutil.cpu_percent(interval=1)
        ram_usage = psutil.virtual_memory().percent
        embed.add_field(name="CPU usage", value=f"{cpu_usage}%", inline=True)
        embed.add_field(name="RAM usage", value=f"{ram_usage}%", inline=True)

        embed.set_footer(text="Made in Vietnam by Xuan Quang", icon_url=footer_image_url)
        await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(About(bot))