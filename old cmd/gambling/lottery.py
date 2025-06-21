import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import random
import math

# Cog Lottery: quản lý lệnh mua vé số và quay thưởng
class Lottery(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Collection lưu thông tin vé số (khác với collection tiền trong mongo_handler)
        self.lottery_collection = self.bot.mongo_handler.db["lottery_tickets"]
        # Các thông số
        self.max_tickets = 10
        # Tính giá vé cơ bản p0 sao cho tổng 10 vé = 250,000
        # p0 = 250000 / (2^10 - 1)
        self.base_price = 250000 / (2**10 - 1)
        # Biến lưu vòng quay (round) vừa xử lý để không chạy lại nhiều lần trong ngày
        self.last_draw_round = None
        self.lottery_draw_task.start()

    def get_current_round(self) -> str:
        # Lấy thời gian hiện tại theo UTC và chuyển đổi sang UTC+7
        now = datetime.utcnow() + timedelta(hours=7)
        # Sử dụng định dạng YYYY-MM-DD làm mã vòng quay
        return now.strftime("%Y-%m-%d")

    @commands.command(name="lottery")
    async def lottery(self, ctx: commands.Context, ticket_code: str):
        """
        !lottery <ticket_code>: Mua vé số với mã 6 chữ số.
        Ví dụ: !lottery 123456
        """
        # Kiểm tra mã vé: phải là số và đúng 6 chữ số
        if not ticket_code.isdigit() or len(ticket_code) != 6:
            await ctx.send("Vui lòng nhập mã vé hợp lệ gồm 6 chữ số (ví dụ: 123456).")
            return

        current_round = self.get_current_round()
        user_id = str(ctx.author.id)
        # Đếm số vé đã mua của user trong vòng quay hiện tại
        ticket_count = self.lottery_collection.count_documents({"round": current_round, "user_id": user_id})
        if ticket_count >= self.max_tickets:
            await ctx.send("Bạn đã mua đủ 10 vé số cho vòng quay này.")
            return

        # Tính giá vé cho vé tiếp theo: price = base_price * (2^ticket_count)
        price = int(self.base_price * (2 ** ticket_count))
        # Lấy dữ liệu người dùng từ collection tiền (theo mongo_handler)
        user_data = self.bot.mongo_handler.get_user_data(user_id)
        balance = user_data.get("balance", 0)
        if balance < price:
            await ctx.send(f"Bạn không có đủ tiền để mua vé số này. Giá vé hiện tại: {price}, số dư: {balance}.")
            return

        # Trừ tiền trong tài khoản (cập nhật mới số dư)
        new_balance = balance - price
        self.bot.mongo_handler.update_user_data(user_id, {"balance": new_balance})
        
        # Lưu thông tin vé vào collection lottery_tickets
        ticket_doc = {
            "round": current_round,
            "user_id": user_id,
            "ticket_code": ticket_code,
            "price": price,
            "timestamp": datetime.utcnow()  # lưu thời gian mua vé (UTC)
        }
        self.lottery_collection.insert_one(ticket_doc)

        await ctx.send(f"UID của bạn: {user_id}\nĐã mua vé số `{ticket_code}` với giá {price}. (Vé số thứ {ticket_count+1}/10)")

    @tasks.loop(minutes=1)
    async def lottery_draw_task(self):
        # Task chạy mỗi phút, kiểm tra xem đã đến 18:00 (UTC+7) của ngày chưa
        now = datetime.utcnow() + timedelta(hours=7)
        current_round = self.get_current_round()
        # Nếu giờ là 18:00 và chưa xử lý vòng quay này
        if now.hour == 18 and now.minute == 0 and self.last_draw_round != current_round:
            self.last_draw_round = current_round  # đánh dấu đã quay cho vòng này

            # Sinh 8 số trúng thưởng ngẫu nhiên, đảm bảo không trùng
            winning_numbers_int = random.sample(range(1, 1000000), 8)
            winning_numbers = [f"{num:06d}" for num in winning_numbers_int]

            # Map giải thưởng theo thứ tự trong danh sách
            prizes = {
                winning_numbers[0]: 500000000,  # giải đặc biệt
                winning_numbers[1]: 10000000,   # giải nhất
                winning_numbers[2]: 5000000,    # giải nhì
                winning_numbers[3]: 1000000,    # giải ba
                winning_numbers[4]: 400000,     # giải tư
                winning_numbers[5]: 200000,     # giải năm
                winning_numbers[6]: 100000,     # giải sáu
                winning_numbers[7]: 40000       # giải bảy
            }

            # Lấy tất cả vé của vòng quay hiện tại
            tickets = list(self.lottery_collection.find({"round": current_round}))
            winners = {}  # dict lưu uid: list các tuple (ticket_code, prize)
            for ticket in tickets:
                code = ticket.get("ticket_code")
                uid = ticket.get("user_id")
                if code in prizes:
                    prize = prizes[code]
                    # Cộng tiền thưởng cho người chơi
                    user_data = self.bot.mongo_handler.get_user_data(uid)
                    current_balance = user_data.get("balance", 0)
                    new_balance = current_balance + prize
                    self.bot.mongo_handler.update_user_data(uid, {"balance": new_balance})
                    # Ghi nhận người thắng
                    if uid not in winners:
                        winners[uid] = []
                    winners[uid].append((code, prize))

            # Gửi DM thông báo kết quả cho từng người thắng
            for uid, win_list in winners.items():
                try:
                    user = await self.bot.fetch_user(int(uid))
                    details = "\n".join([f"Vé số `{code}` trúng {prize:,} đồng" for code, prize in win_list])
                    message = f"Kết quả quay số ngày {current_round}:\n{details}"
                    await user.send(message)
                except Exception as e:
                    print(f"Lỗi gửi DM cho UID {uid}: {e}")

            # (Tùy chọn) Gửi thông báo kết quả vào một kênh log nếu cần:
            # VD: log_channel_id = 123456789012345678
            log_channel_id = 123456789012345678  # thay bằng ID kênh log của bạn nếu có
            log_channel = self.bot.get_channel(log_channel_id)
            if log_channel:
                result_msg = "Kết quả quay số:\n"
                for num, prize in prizes.items():
                    result_msg += f"Vé số `{num}` trúng {prize:,} đồng\n"
                await log_channel.send(result_msg)

            # Sau khi xử lý, xóa tất cả vé của vòng quay này
            self.lottery_collection.delete_many({"round": current_round})

    @lottery_draw_task.before_loop
    async def before_lottery_draw(self):
        await self.bot.wait_until_ready()

async def setup(bot: commands.Bot):
    await bot.add_cog(Lottery(bot))
