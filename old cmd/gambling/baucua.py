import discord
from discord.ext import commands
import asyncio
import random
import datetime

class BauCuaModal(discord.ui.Modal):
    def __init__(self, choice_label: str, session: dict, user_id: str):
        super().__init__(title="Đặt Cược Bầu Cua")
        self.choice = choice_label.lower()
        self.session = session
        self.user_id = user_id

        self.amount_input = discord.ui.TextInput(
            label="Số ecoin cược",
            placeholder="Nhập số ecoin bạn muốn cược...",
            style=discord.TextStyle.short
        )
        self.add_item(self.amount_input)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            amt = int(self.amount_input.value)
            if amt <= 0:
                raise ValueError
        except ValueError:
            await interaction.response.send_message(
                "Số ecoin không hợp lệ.",
                ephemeral=True
            )
            return

        mongo_handler = interaction.client.mongo_handler
        user_data = mongo_handler.get_user_data(self.user_id) or {}
        balance = user_data.get('balance', 0)

        if self.user_id not in self.session["bets"]:
            self.session["bets"][self.user_id] = {
                "nai": 0,
                "bầu": 0,
                "gà": 0,
                "cá": 0,
                "cua": 0,
                "tôm": 0
            }

        current_bet = self.session["bets"][self.user_id][self.choice]
        limit = 250000
        allowed_remaining = limit - current_bet

        if allowed_remaining <= 0:
            await interaction.response.send_message(
                f"Bạn **đã đặt cược đến giới hạn** của {self.choice.title()}.",
                ephemeral=True
            )
            return

        accepted_amount = amt if amt <= allowed_remaining else allowed_remaining

        if balance < accepted_amount:
            await interaction.response.send_message(
                "<:x_:1335734856734347355> Bạn không có đủ ecoin để cược.",
                ephemeral=True
            )
            return

        new_balance = balance - accepted_amount
        mongo_handler.update_user_data(self.user_id, {'balance': new_balance})

        self.session["bets"][self.user_id][self.choice] += accepted_amount

        if amt > accepted_amount:
            await interaction.response.send_message(
                f"<:check_mark:1335734939185975378> **|** Bạn đã đặt **__{accepted_amount:,}__** ecoin vào **{self.choice.title()}**.",
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"<:check_mark:1335734939185975378> **|** Bạn đã đặt thêm **__{accepted_amount:,}__** ecoin vào **{self.choice.title()}**.",
                ephemeral=True
            )

class BauCuaButton(discord.ui.Button):
    def __init__(self, label: str, emoji: str, session: dict):
        super().__init__(style=discord.ButtonStyle.primary, label=label, emoji=emoji)
        self.choice = label
        self.session = session

    async def callback(self, interaction: discord.Interaction):
        modal = BauCuaModal(self.choice, self.session, str(interaction.user.id))
        await interaction.response.send_modal(modal)

class BauCuaView(discord.ui.View):
    def __init__(self, session: dict):
        super().__init__(timeout=None)
        self.session = session

        emoji_dict = {
            "Nai": "<:deer:1331545065994194954>",
            "Bầu": "<:gourd:1331553443617443933>",
            "Gà": "<:chicken:1331562683593523260>",
            "Cá": "<:fish_1:1331553258594111508>",
            "Cua": "<:crab:1331553322997649518>",
            "Tôm": "<:shrimp:1331553360301523056>"
        }
        choices = ["Nai", "Bầu", "Gà", "Cá", "Cua", "Tôm"]
        for choice in choices:
            button = BauCuaButton(choice, emoji_dict[choice], session)
            self.add_item(button)

    def disable_all_buttons(self):
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

class BauCua(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_sessions = {}

    @commands.command(name='baucua', aliases=['bc'])
    async def baucua(self, ctx):
        guild_id = str(ctx.guild.id)
        user_id = str(ctx.author.id)

        if guild_id not in self.active_sessions:
            self.active_sessions[guild_id] = {}

        if user_id in self.active_sessions[guild_id]:
            await ctx.send(
                f"<:clock:1328107133551513660> {ctx.author.mention}, bạn đã có một phiên chưa kết thúc. "
                "Vui lòng chờ phiên đó kết thúc trước khi mở phiên mới."
            )
            return

        session = {
            "owner": user_id,
            "bets": {},
            "aborted": False
        }
        self.active_sessions[guild_id][user_id] = session

        tz_plus7 = datetime.timezone(datetime.timedelta(hours=7))
        time_until_close = int((datetime.datetime.now(tz_plus7) + datetime.timedelta(seconds=60)).timestamp())

        embed = discord.Embed(
            title=f"<a:baucua_shuffle:1331562024043413576> BẦU CUA <a:baucua_shuffle:1331562024043413576>",
            description=(
                "Hãy đặt cược bằng cách **nhấn vào nút** bên dưới!\n\n"
                f"Thời gian đặt cược còn lại: <t:{time_until_close}:R>\n"
                "Nai: 0 <:ecoin:1327329353163604081>\n"
                "Bầu: 0 <:ecoin:1327329353163604081>\n"
                "Gà: 0 <:ecoin:1327329353163604081>\n"
                "Cá: 0 <:ecoin:1327329353163604081>\n"
                "Cua: 0 <:ecoin:1327329353163604081>\n"
                "Tôm: 0 <:ecoin:1327329353163604081>"
            ),
            color=0xFFCCFF
        )

        view = BauCuaView(session)
        original_message = await ctx.send(embed=embed, view=view)

        emoji_mapping = {
            "nai": "<:deer:1331545065994194954>",
            "bầu": "<:gourd:1331553443617443933>",
            "gà": "<:chicken:1331562683593523260>",
            "cá": "<:fish_1:1331553258594111508>",
            "cua": "<:crab:1331553322997649518>",
            "tôm": "<:shrimp:1331553360301523056>"
        }

        async def update_embed_counts():
            while True:
                if session["aborted"]:
                    break

                counts = {"nai": 0, "bầu": 0, "gà": 0, "cá": 0, "cua": 0, "tôm": 0}
                for uid, bet_dict in session["bets"].items():
                    for choice, amt in bet_dict.items():
                        counts[choice] += amt

                description = (
                    "Hãy đặt cược của bạn bằng cách **nhấn vào nút** bên dưới!\n\n"
                    f"<:clock:1328107133551513660> Thời gian đặt cược còn lại: <t:{time_until_close}:R>\n"
                )
                for choice, total in counts.items():
                    description += (
                        f"{emoji_mapping[choice]} {choice.title()}: {total:,} <:ecoin:1327329353163604081>\n"
                    )
                embed.description = description

                try:
                    await original_message.edit(embed=embed)
                except discord.NotFound:
                    session["aborted"] = True
                    break

                await asyncio.sleep(5)

        update_task = asyncio.create_task(update_embed_counts())

        await asyncio.sleep(60)
        update_task.cancel()

        if session["aborted"]:
            await ctx.send(f"<:x_:1335734856734347355> Phiên Bầu Cua của {ctx.author.mention} đã bị hủy (tin nhắn gốc không còn).")
            del self.active_sessions[guild_id][user_id]
            if not self.active_sessions[guild_id]:
                del self.active_sessions[guild_id]
            return

        bets = session["bets"]
        if len(bets) < 2:
            for uid, bet_dict in bets.items():
                user_data = self.bot.mongo_handler.get_user_data(uid) or {}
                balance = user_data.get('balance', 0)
                balance += sum(bet_dict.values())
                self.bot.mongo_handler.update_user_data(uid, {'balance': balance})

            try:
                await original_message.reply(
                    f"<:x_:1335734856734347355> {ctx.author.mention}, không đủ người tham gia cược! Tiền cược được hoàn trả."
                )
                view.disable_all_buttons()
                await original_message.edit(embed=embed, view=view)
            except discord.NotFound:
                pass

            del self.active_sessions[guild_id][user_id]
            if not self.active_sessions[guild_id]:
                del self.active_sessions[guild_id]
            return

        view.disable_all_buttons()
        try:
            await original_message.edit(embed=embed, view=view)
        except discord.NotFound:
            session["aborted"] = True

        if session["aborted"]:
            await ctx.send(f"<:x_:1335734856734347355> Phiên Bầu Cua của {ctx.author.mention} đã bị hủy (tin nhắn gốc không còn).")
            del self.active_sessions[guild_id][user_id]
            if not self.active_sessions[guild_id]:
                del self.active_sessions[guild_id]
            return

        shuffle_emoji = "<a:baucua_shuffle:1331562024043413576>"
        outcomes = ["nai", "bầu", "gà", "cá", "cua", "tôm"]
        result = [random.choice(outcomes) for _ in range(3)]

        try:
            reveal = [shuffle_emoji] * 3
            reveal_message = await original_message.reply(" ".join(reveal))
            for i in range(3):
                reveal[i] = emoji_mapping[result[i]]
                await asyncio.sleep(1)
                await reveal_message.edit(content=" ".join(reveal))

            final_result_string = "-".join(result).upper()
            await original_message.reply(f"Kết quả: **{final_result_string}**")
        except discord.NotFound:
            session["aborted"] = True

        if session["aborted"]:
            await ctx.send(f"<:x_:1335734856734347355> Phiên Bầu Cua của {ctx.author.mention} bị hủy (tin nhắn gốc không còn).")
            del self.active_sessions[guild_id][user_id]
            if not self.active_sessions[guild_id]:
                del self.active_sessions[guild_id]
            return

        winners_info = []
        for uid, bet_dict in bets.items():
            total_bet_of_user = sum(bet_dict.values())
            total_win = 0
            detail_wins = []

            for choice, bet_amt in bet_dict.items():
                if bet_amt <= 0:
                    continue
                occurrences = result.count(choice)
                if occurrences == 1:
                    money_won = 2 * bet_amt
                elif occurrences == 2:
                    money_won = 3 * bet_amt
                elif occurrences == 3:
                    money_won = 4 * bet_amt
                else:
                    money_won = 0

                if money_won > 0:
                    total_win += money_won
                    detail_wins.append((choice, bet_amt, money_won))

            if total_win > 0:
                user_data = self.bot.mongo_handler.get_user_data(uid) or {}
                balance = user_data.get('balance', 0)
                balance += total_win
                self.bot.mongo_handler.update_user_data(uid, {'balance': balance})

                winners_info.append((uid, total_bet_of_user, detail_wins))

        embed_result = discord.Embed(
            title="<:bar_chart:1331687032833048637> Thống Kê Kết Quả <:bar_chart:1331687032833048637>",
            description=f"Phiên do {ctx.author.mention} tạo đã kết thúc!",
            color=0x00ff00
        )

        if winners_info:
            winners_str = ""
            for (uid, total_bet, detail_wins) in winners_info:
                member_obj = ctx.guild.get_member(int(uid))
                mention_name = member_obj.mention if member_obj else f"<@{uid}>"

                winners_str += f"**{mention_name}**\n"
                winners_str += f"> Tổng cược: **{total_bet:,}** <:ecoin:1327329353163604081>\n"
                for (choice, bet_amt, money_won) in detail_wins:
                    winners_str += (
                        f"> • {choice.title()}: Cược {bet_amt:,} <:ecoin:1327329353163604081>, "
                        f"thắng {money_won:,} <:ecoin:1327329353163604081>\n"
                    )
                winners_str += "\n"

            embed_result.add_field(
                name="Người Thắng",
                value=winners_str.strip(),
                inline=False
            )
        else:
            embed_result.add_field(
                name="Người Thắng",
                value="Không có ai thắng phiên này.",
                inline=False
            )

        participants = []
        for uid in bets.keys():
            mem = ctx.guild.get_member(int(uid))
            participants.append(mem.mention if mem else f"<@{uid}>")

        if participants:
            embed_result.add_field(
                name="Danh Sách Người Chơi",
                value=", ".join(participants),
                inline=False
            )

        try:
            await original_message.reply(embed=embed_result)
        except discord.NotFound:
            session["aborted"] = True

        if session["aborted"]:
            await ctx.send(f"<:x_:1335734856734347355> Phiên Bầu Cua của {ctx.author.mention} đã bị hủy (tin nhắn gốc không còn).")

        del self.active_sessions[guild_id][user_id]
        if not self.active_sessions[guild_id]:
            del self.active_sessions[guild_id]

async def setup(bot):
    await bot.add_cog(BauCua(bot))
