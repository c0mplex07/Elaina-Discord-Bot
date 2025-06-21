import discord
from discord.ext import commands
from discord.ui import Button, View
import random
import logging
import asyncio

logger = logging.getLogger(__name__)

class Blackjack(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logs_channel_id = 1333492348331757579 

        self.card_values = {
            '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10,
            'J': 10, 'Q': 10, 'K': 10, 'A': 11
        }

        self.card_emojis = {
            '2H': '<:2H:1332053050956709984>', '2D': '<:2D:1332053049195364403>',
            '2C': '<:2C:1332053047190229023>', '2S': '<:2S:1332053054157230141>',
            '3H': '<:3H:1332053061560045578>', '3D': '<:3D:1332053059341127782>',
            '3C': '<:3C:1332053056673681529>', '3S': '<:3S:1332053064525414542>',
            '4H': '<:4H:1332053135145042012>', '4D': '<:4D:1332053132573671597>',
            '4C': '<:4C:1332053129881194607>', '4S': '<:4S:1332053138714394766>',
            '5H': '<:5H:1332053171031375956>', '5D': '<:5D:1332053144938614937>',
            '5C': '<:5C:1332053142090678415>', '5S': '<:5S:1332053173296173190>',
            '6H': '<:6H:1332053181722787941>', '6D': '<:6D:1332053178748764160>',
            '6C': '<:6C:1332053175833726987>', '6S': '<:6S:1332053184532844716>',
            '7H': '<:7H:1332053194788048926>', '7D': '<:7D:1332053190656397312>',
            '7C': '<:7C:1332053187644883055>', '7S': '<:7S:1332053198135103509>',
            '8H': '<:8H:1332053206381101177>', '8D': '<:8D:1332053203675774997>',
            '8C': '<:8C:1332053201712709732>', '8S': '<:8S:1332053209052745850>',
            '9H': '<:9H:1332053300471664640>', '9D': '<:9D:1332053297267347467>',
            '9C': '<:9C:1332053294914342993>', '9S': '<:9S:1332053303118401666>',
            '10H': '<:10H:1332053312475758684>', '10D': '<:10D:1332053309153873931>',
            '10C': '<:10C:1332053306167787641>', '10S': '<:10S:1332053315009253487>',
            'JH': '<:JH:1332053393572757546>', 'JD': '<:JD:1332053390070386699>',
            'JC': '<:JC:1332053385414840360>', 'JS': '<:JS:1332053397859205204>',
            'QH': '<:QH:1332053807055638540>', 'QD': '<:QD:1332053804237197352>',
            'QC': '<:QC:1332053413436985364>', 'QS': '<:QS:1332053810050367549>',
            'KH': '<:KH:1332053407015506081>', 'KD': '<:KD:1332053401818759251>',
            'KC': '<:KC:1332053399973138442>', 'KS': '<:KS:1332053404205187082>',
            'AH': '<:AH:1332053325859913871>', 'AD': '<:AD:1332053323292999730>',
            'AC': '<:AC:1332053317618110535>', 'AS': '<:AS:1332053329194258464>',
        }

        self.hidden_card_placeholder = '<:deck_card:1332053831810289767>'
        self.active_games = {}

    def deal_card(self):
        return random.choice(list(self.card_emojis.keys()))

    def calculate_score(self, cards):
        total = sum(self.card_values[card[:-1]] for card in cards)
        aces = sum(1 for card in cards if card[:-1] == 'A')
        while total > 21 and aces > 0:
            total -= 10
            aces -= 1
        return total

    def deal_initial_dealer_cards(self):
        dealer_cards = [self.deal_card(), self.deal_card()]
        score = self.calculate_score(dealer_cards)
        while score < 17 or score > 21:
            dealer_cards = [self.deal_card(), self.deal_card()]
            score = self.calculate_score(dealer_cards)
        return dealer_cards

    def has_blackjack(self, cards):
        return len(cards) == 2 and self.calculate_score(cards) == 21

    def dealer_optimal_decision(self, dealer_cards):
        return self.calculate_score(dealer_cards) < 18

    async def send_blackjack_log(self, ctx, outcome, bet_amount, user_data):
        log_channel = self.bot.get_channel(self.logs_channel_id)
        if log_channel:
            embed = discord.Embed(
                title="Blackjack Log",
                color=discord.Color.blue(),
                timestamp=discord.utils.utcnow()
            )
            embed.add_field(name="Người chơi", value=ctx.author.mention, inline=True)
            embed.add_field(name="Kết quả", value=outcome, inline=True)
            embed.add_field(name="Tiền cược", value=f"{format(bet_amount, ',')} ecoin", inline=True)
            embed.add_field(name="Số dư còn lại", value=f"{format(user_data.get('balance', 0), ',')} ecoin", inline=True)
            embed.set_footer(text="Thời gian cược")
            await log_channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message):
        for user_id, game_state in list(self.active_games.items()):
            if game_state["message"].id == message.id and not game_state.get("finished", False):
                bet = game_state["bet"]
                user_data = game_state["user_data"]
                user_data['balance'] += bet
                self.bot.mongo_handler.update_user_data(user_id, user_data)
                channel = self.bot.get_channel(game_state.get("channel_id"))
                if channel:
                    await channel.send(f"<:check_mark:1335734939185975378> {game_state.get('username')} Game của bạn bị hủy, đã hoàn trả {format(bet, ',')} ecoin.")
                del self.active_games[user_id]

    @commands.command(name='blackjack', aliases=['bj'])
    async def blackjack(self, ctx, bet: str = None):
        user_id = str(ctx.author.id)
        if user_id in self.active_games:
            await ctx.send("<:x_:1335734856734347355> Bạn đang có một phiên Blackjack chưa hoàn thành.")
            return

        try:
            user_data = self.bot.mongo_handler.get_user_data(user_id)
            user_balance = user_data.get('balance', 0)
            if user_balance <= 0:
                await ctx.send("<:x_:1335734856734347355> Bạn không có đủ ecoin để cược.")
                return

            if not bet:
                await ctx.send("`eblackjack <số tiền cược>` hoặc `eblackjack all`")
                return

            MAX_BET = 250000
            if bet.lower() == 'all':
                bet_amount = min(user_balance, MAX_BET)
            else:
                try:
                    bet_amount = int(bet)
                    if bet_amount <= 0:
                        await ctx.send("<:x_:1335734856734347355> Số tiền đặt cược phải lớn hơn 0.")
                        return
                    bet_amount = min(bet_amount, MAX_BET)
                except ValueError:
                    await ctx.send("<:x_:1335734856734347355> Vui lòng nhập một số tiền hợp lệ hoặc 'all'.")
                    return

            if bet_amount > user_balance:
                await ctx.send("<:x_:1335734856734347355> Bạn không có đủ ecoin để đặt cược.")
                return

            user_data['balance'] -= bet_amount
            self.bot.mongo_handler.update_user_data(user_id, user_data)

            dealer_cards = self.deal_initial_dealer_cards()
            player_cards = [self.deal_card(), self.deal_card()]
            player_score = self.calculate_score(player_cards)
            while player_score >= 10:
                player_cards = [self.deal_card(), self.deal_card()]
                player_score = self.calculate_score(player_cards)

            embed = discord.Embed(title="", color=None)
            embed.set_author(name=f"{ctx.author.display_name} cược {format(bet_amount, ',')} ecoin vào Blackjack!", icon_url=ctx.author.display_avatar.url)
            embed.add_field(name=f"**{ctx.author.display_name} [- {player_score}-]**", value=' '.join([self.card_emojis[card] for card in player_cards]), inline=False)
            embed.add_field(name="**Dealer [- ?-]**", value=f"{self.card_emojis[dealer_cards[0]]} {self.hidden_card_placeholder}", inline=False)

            view = View(timeout=180)
            hit_button = Button(label="Rút bài", style=discord.ButtonStyle.success)
            stand_button = Button(label="Dừng", style=discord.ButtonStyle.danger)
            view.add_item(hit_button)
            view.add_item(stand_button)

            game_message = await ctx.send(embed=embed, view=view)
            self.active_games[user_id] = {
                "message": game_message, "bet": bet_amount, "user_data": user_data,
                "channel_id": ctx.channel.id, "username": ctx.author.mention, "finished": False
            }

            async def disable_buttons():
                hit_button.disabled = True
                stand_button.disabled = True
                await game_message.edit(embed=embed, view=view)

            async def hit_callback(interaction: discord.Interaction):
                nonlocal game_message
                if interaction.user != ctx.author:
                    await interaction.response.send_message("<:x_:1335734856734347355> Bạn không có quyền tương tác!", ephemeral=True)
                    return
                if not interaction.response.is_done():
                    await interaction.response.defer()

                player_cards.append(self.deal_card())
                new_player_score = self.calculate_score(player_cards)
                embed.set_field_at(0, name=f"**{ctx.author.display_name} [- {new_player_score}-]**", value=' '.join([self.card_emojis[card] for card in player_cards]), inline=False)

                if new_player_score > 21:
                    embed.set_footer(text=f"Bạn đã thua! (-{format(bet_amount, ',')})")
                    embed.color = discord.Color(int("FF0000", 16))
                    await self.send_blackjack_log(ctx, "Busted - Thua", bet_amount, user_data)
                    await disable_buttons()
                    self.active_games[user_id]["finished"] = True
                    del self.active_games[user_id]
                await game_message.edit(embed=embed, view=view)

            async def stand_callback(interaction: discord.Interaction):
                nonlocal game_message
                if interaction.user != ctx.author:
                    await interaction.response.send_message("<:x_:1335734856734347355> Bạn không có quyền tương tác!", ephemeral=True)
                    return
                if not interaction.response.is_done():
                    await interaction.response.defer()

                hit_button.disabled = True
                stand_button.disabled = True
                await game_message.edit(embed=embed, view=view)

                final_player_score = self.calculate_score(player_cards)
                dealer_score = self.calculate_score(dealer_cards)
                full_dealer = ' '.join([self.card_emojis[card] for card in dealer_cards])
                embed.set_field_at(1, name=f"**Dealer [- {dealer_score}-]**", value=full_dealer, inline=False)

                if self.has_blackjack(dealer_cards) and not self.has_blackjack(player_cards):
                    embed.set_footer(text=f"Bạn đã thua! Dealer có Blackjack! (-{format(bet_amount, ',')})")
                    embed.color = discord.Color(int("FF0000", 16))
                    outcome = "Thua (Dealer Blackjack)"
                else:
                    while self.dealer_optimal_decision(dealer_cards):
                        await asyncio.sleep(1)
                        dealer_cards.append(self.deal_card())
                        dealer_score = self.calculate_score(dealer_cards)
                        full_dealer = ' '.join([self.card_emojis[card] for card in dealer_cards])
                        embed.set_field_at(1, name=f"**Dealer [- {dealer_score}-]**", value=full_dealer, inline=False)
                        await game_message.edit(embed=embed, view=view)

                    if dealer_score > 21:
                        embed.set_footer(text=f"Chúc mừng, bạn thắng! Dealer bị quá số! (+{format(bet_amount, ',')})")
                        outcome = "Thắng (Dealer Busted)"
                        user_data['balance'] += bet_amount * 2
                        embed.color = discord.Color(int("00FF00", 16))
                    elif dealer_score == final_player_score:
                        embed.set_footer(text="Hòa!")
                        outcome = "Hòa"
                        user_data['balance'] += bet_amount
                        embed.color = None
                    elif dealer_score > final_player_score:
                        embed.set_footer(text=f"Bạn đã thua! Dealer thắng! (-{format(bet_amount, ',')})")
                        outcome = "Thua"
                        embed.color = discord.Color(int("FF0000", 16))
                    else:
                        embed.set_footer(text=f"Chúc mừng, bạn thắng! (+{format(bet_amount, ',')})")
                        outcome = "Thắng"
                        user_data['balance'] += bet_amount * 2
                        embed.color = discord.Color(int("00FF00", 16))

                self.bot.mongo_handler.update_user_data(user_id, user_data)
                await self.send_blackjack_log(ctx, outcome, bet_amount, user_data)
                await disable_buttons()
                self.active_games[user_id]["finished"] = True
                del self.active_games[user_id]

            hit_button.callback = hit_callback
            stand_button.callback = stand_callback

        except Exception as e:
            logger.exception("Lỗi khi thực hiện trò chơi Blackjack")
            await ctx.send(f"Đã có lỗi xảy ra: {str(e)}")
            if user_id in self.active_games and not self.active_games[user_id].get("finished", False):
                self.active_games[user_id]["user_data"]['balance'] += self.active_games[user_id]["bet"]
                self.bot.mongo_handler.update_user_data(user_id, self.active_games[user_id]["user_data"])
                del self.active_games[user_id]

async def setup(bot):
    await bot.add_cog(Blackjack(bot))