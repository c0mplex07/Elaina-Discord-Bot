import discord
from discord.ext import commands
import random
import asyncio
import logging
import time
import os

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class CoinFlip(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.emoji_flip = "<a:coinflip:1327858078569201695>"
        self.emoji_heads = "<:coinflip_heads:1327870826753560618>"
        self.emoji_tails = "<:coinflip_tails:1327703607792898048>"
        self.active_flips = set()
        self.cooldown_notifications = {}
        self.logs_channel_id = int(os.getenv("LOGS_CHANNEL_ID", 1333492847391014923))
        self.MAX_BET = 250000

    @commands.command(name="coinflip", aliases=['cf'])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def coinflip(self, ctx, so_tien: str = None):
        if ctx.author.id in self.active_flips:
            await ctx.send("<:x_:1335734856734347355> Lệnh coinflip của bạn vẫn đang thực hiện.")
            return

        self.active_flips.add(ctx.author.id)

        try:
            user_id = str(ctx.author.id)
            user_data = self.bot.mongo_handler.get_user_data(user_id)
            user_balance = user_data.get('balance', 0)

            if user_balance <= 0:
                await ctx.send("<:x_:1335734856734347355> Bạn không có đủ ecoin để cược.")
                return

            if so_tien is None:
                await ctx.send("`ecoinflip <số tiền cược>` hoặc `ecoinflip all`")
                return

            if so_tien.lower() == 'all':
                bet_amount = min(user_balance, self.MAX_BET)
            else:
                try:
                    bet_amount = int(so_tien)
                    if bet_amount <= 0:
                        await ctx.send("<:x_:1335734856734347355> Số tiền đặt cược phải lớn hơn 0.")
                        return
                    bet_amount = min(bet_amount, self.MAX_BET, user_balance)
                except ValueError:
                    await ctx.send("<:x_:1335734856734347355> Vui lòng nhập một số tiền hợp lệ hoặc 'all' để đặt cược tất cả.")
                    return

            if bet_amount > user_balance:
                await ctx.send("<:x_:1335734856734347355> Bạn không có đủ ecoin để đặt cược.")
                return

            flipping_message = await ctx.send(f"{self.emoji_flip} Tung đồng xu...")
            await asyncio.sleep(1.5)

            random_probability = random.random()
            if random_probability < 0.5:
                result_emoji = self.emoji_heads
                result_text = "mặt ngửa"
                user_data['balance'] += bet_amount
                result_message = (f"Đồng xu rơi ra **{result_text}** {result_emoji}\n"
                                  f"Bạn đã thắng __**{bet_amount:,}**__ ecoin!")
            else:
                result_emoji = self.emoji_tails
                result_text = "mặt úp"
                user_data['balance'] -= bet_amount
                result_message = (f"Rất tiếc, đồng xu rơi ra **{result_text}** {result_emoji}\n"
                                  f"Bạn đã thua __**{bet_amount:,}**__ ecoin.")

            self.bot.mongo_handler.update_user_data(user_id, user_data)
            await flipping_message.edit(content=result_message)

            log_channel = self.bot.get_channel(self.logs_channel_id)
            if log_channel:
                embed = discord.Embed(
                    title="CoinFlip Log",
                    color=discord.Color.blue(),
                    timestamp=discord.utils.utcnow()
                )
                embed.add_field(name="Người chơi", value=ctx.author.mention, inline=True)
                embed.add_field(name="Tiền cược", value=f"{bet_amount:,} ecoin", inline=True)
                embed.add_field(name="Kết quả", value=f"{result_text} {result_emoji}", inline=True)
                embed.add_field(name="Số dư còn lại", value=f"{user_data.get('balance', 0):,} ecoin", inline=True)
                embed.set_footer(text="Thời gian cược")
                await log_channel.send(embed=embed)

        finally:
            self.active_flips.remove(ctx.author.id)

    @coinflip.error
    async def coinflip_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            if ctx.author.id in self.cooldown_notifications:
                return

            retry_after = error.retry_after
            timestamp = int(time.time() + retry_after)
            await ctx.send(f"<:clock:1328107133551513660> **|** Vui lòng chờ đến <t:{timestamp}:R> trước khi sử dụng lệnh này.")

            self.cooldown_notifications[ctx.author.id] = timestamp
            self.bot.loop.call_later(retry_after, lambda: self.cooldown_notifications.pop(ctx.author.id, None))

async def setup(bot):
    await bot.add_cog(CoinFlip(bot))
