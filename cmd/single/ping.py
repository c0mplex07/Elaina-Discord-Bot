import discord
from discord.ext import commands
import time

class Ping(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name='ping')
    async def ping(self, ctx):
        start_time = time.time()
        
        message = await ctx.send("Pinging...")
        end_time = time.time()

        bot_latency = round((end_time - start_time) * 1000)
        api_latency = round(self.bot.latency * 1000)

        await message.edit(content=f"Độ trễ Bot: `{bot_latency}ms`\nĐộ trễ API: `{api_latency}ms`")

async def setup(bot):
    await bot.add_cog(Ping(bot))