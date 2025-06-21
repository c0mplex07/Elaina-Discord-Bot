import discord
from discord.ext import commands
import random
import asyncio
import logging
import time

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class Taixiu(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.dice_emojis = {
            1: "<:xx1:1327639752433729566>",
            2: "<:xx2:1327639801263820881>",
            3: "<:xx3:1327639827440734279>",
            4: "<:xx4:1327639852694372403>",
            5: "<:xx5:1327639896910987264>",
            6: "<:xx6:1327639928892424235>"
        }
        self.active_games = {}
        self.json_handler = self.bot.mongo_handler
        self.logs_channel_id = 1333464237296848947
        self.MAX_BET = 250000

    @commands.command(name="taixiu", aliases=['tx'])
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def taixiu(self, ctx, bet_type: str = None, bet_amount: str = "0"):
        if ctx.author.id in self.active_games:
            remaining_time = self.active_games[ctx.author.id] - time.time()
            if remaining_time > 0:
                target_timestamp = int(self.active_games[ctx.author.id])
                await ctx.send(f"<:clock:1328107133551513660> Vui lòng chờ đến <t:{target_timestamp}:R> để tiếp tục.")
                return

        user_id = str(ctx.author.id)
        user_data = self.json_handler.get_user_data(user_id)
        user_balance = user_data.get('balance', 0)

        if bet_amount.lower() == "all":
            if user_balance <= 0:
                await ctx.send("<:x_:1335734856734347355> Bạn không có đủ ecoin để cược.")
                return
            bet_amount_int = min(user_balance, self.MAX_BET)
        else:
            try:
                bet_amount_int = int(bet_amount)
            except ValueError:
                await ctx.send("<:x_:1335734856734347355> Số tiền cược không hợp lệ.")
                return

            if bet_amount_int <= 0 or bet_amount_int > user_balance:
                await ctx.send("<:x_:1335734856734347355> Số tiền đặt cược không hợp lệ.")
                return

            bet_amount_int = min(bet_amount_int, self.MAX_BET, user_balance)
        
        if bet_type is None or bet_type.lower() not in ["tai", "xiu"]:
            await ctx.send("`etaixiu <tai hoặc xiu> <tiền cược>` hoặc `etaixiu <tai hoặc xiu> all`")
            return

        user_data['balance'] -= bet_amount_int
        self.json_handler.update_user_data(user_id, user_data)

        self.active_games[ctx.author.id] = time.time() + 5

        outcome = "tai" if random.random() < 0.5 else "xiu"
        if outcome == "tai":
            target_total = random.randint(11, 18)
        else:
            target_total = random.randint(3, 10)

        while True:
            dice_results = [random.randint(1, 6) for _ in range(3)]
            if sum(dice_results) == target_total:
                break

        placeholder_emoji = "<a:xxrandom:1333470965417377802>"
        message = await ctx.send(f"{placeholder_emoji} {placeholder_emoji} {placeholder_emoji}")
        await asyncio.sleep(2)

        result_emojis = [self.dice_emojis[die] for die in dice_results]
        for i in range(3):
            await asyncio.sleep(0.5)
            remaining_placeholders = " ".join([placeholder_emoji] * (3 - (i + 1)))
            await message.edit(content=f"{' '.join(result_emojis[:i+1])} {remaining_placeholders}")

        result_message = (
            f"{' '.join(result_emojis)}\n"
            f"Tổng điểm: {target_total:,} ({'Tài' if outcome == 'tai' else 'Xỉu'})\n"
        )

        if bet_type.lower() == outcome:
            win_amount = bet_amount_int * 2
            user_data['balance'] += win_amount
            result_message += f"<:ecoin:1327329353163604081> **|** Bạn thắng __**{win_amount:,}**__ ecoin!\n"
        else:
            result_message += f"<:ecoin:1327329353163604081> **|** Bạn thua __**{bet_amount_int:,}**__ ecoin.\n"

        self.json_handler.update_user_data(user_id, user_data)
        await message.edit(content=result_message)

        log_channel = self.bot.get_channel(self.logs_channel_id)
        if log_channel:
            embed = discord.Embed(
                title="Tài Xỉu - Log",
                color=discord.Color.blue(),
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(name="Người chơi", value=ctx.author.mention, inline=True)
            embed.add_field(name="Kết quả", value=f"{'Tài' if outcome == 'tai' else 'Xỉu'} ({target_total:,})", inline=True)
            embed.add_field(name="Tiền cược", value=f"{bet_amount_int:,} ecoin", inline=True)
            embed.add_field(name="Số dư còn lại", value=f"{user_data.get('balance', 0):,} ecoin", inline=True)
            embed.set_footer(text="Thời gian cược")
            await log_channel.send(embed=embed)

        del self.active_games[ctx.author.id]

    @taixiu.error
    async def taixiu_error(self, ctx, error):
        if isinstance(error, commands.CommandOnCooldown):
            await ctx.send("<:clock:1328107133551513660> Vui lòng chờ trước khi sử dụng lệnh này.")

async def setup(bot):
    await bot.add_cog(Taixiu(bot))
