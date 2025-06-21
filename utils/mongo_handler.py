import asyncio
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
import discord
from tenacity import retry, stop_after_attempt, wait_exponential
import logging

logger = logging.getLogger(__name__)

class MongoHandler:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(MongoHandler, cls).__new__(cls)
        return cls._instance

    def __init__(self, uri: str, db_name: str, bot: discord.Client, log_channel_id: int):
        # Kiểm tra nếu đã khởi tạo trước đó thì không thực hiện lại
        if hasattr(self, 'client') and self.client is not None:
            return

        self.uri = uri
        self.db_name = db_name
        self.bot = bot
        self.log_channel_id = log_channel_id
        self.client = None
        self.db = None
        self.collection = None
        self.connect()

    async def log_to_channel(self, message: str):
        """Gửi logs tới kênh Discord được chỉ định."""
        if self.bot.is_ready():
            log_channel = self.bot.get_channel(self.log_channel_id)
            if log_channel:
                try:
                    await log_channel.send(message)
                except Exception as e:
                    logger.error(f"Failed to send log message: {e}")

    def connect(self):
        try:
            # Kết nối MongoDB với cấu hình connection pool tối ưu
            self.client = MongoClient(
                self.uri,
                tls=True,
                tlsAllowInvalidCertificates=True,
                serverSelectionTimeoutMS=5000,
                maxPoolSize=100,      # Giới hạn số kết nối tối đa
                minPoolSize=10,       # Giữ ít nhất 10 kết nối luôn mở
                socketTimeoutMS=30000,
                connectTimeoutMS=30000
            )
            self.db = self.client[self.db_name]
            self.collection = self.db["enoubot"]
            self.client.server_info()  # Kiểm tra kết nối

            # Gửi thông báo kết nối thành công lên Discord
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.log_to_channel(f"✅ Connected to MongoDB: {self.db_name}"))
            else:
                loop.run_until_complete(self.log_to_channel(f"✅ Connected to MongoDB: {self.db_name}"))
        except ServerSelectionTimeoutError:
            asyncio.create_task(self.log_to_channel("❌ MongoDB server is not available."))
        except ConnectionFailure:
            asyncio.create_task(self.log_to_channel("❌ Failed to connect to MongoDB server."))

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def get_user_data(self, user_id: str) -> dict:
        """Lấy dữ liệu người dùng từ MongoDB với cơ chế retry nếu có lỗi."""
        if not self.client:
            self.connect()
        try:
            user_data = self.collection.find_one({"_id": user_id})
            if user_data:
                user_data.pop("_id", None)  # Loại bỏ trường _id khỏi kết quả
                return user_data
            return {}
        except ServerSelectionTimeoutError as e:
            logger.error("MongoDB server timeout. Retrying...", exc_info=e)
            raise

    def update_user_data(self, user_id: str, update_fields: dict) -> None:
        """Cập nhật dữ liệu người dùng trong MongoDB."""
        if not self.client:
            self.connect()
        try:
            self.collection.update_one(
                {"_id": user_id},
                {"$set": update_fields},
                upsert=True
            )
        except ServerSelectionTimeoutError:
            asyncio.create_task(self.log_to_channel("❌ Failed to update data, server is not available."))

    def delete_user_data(self, user_id: str) -> None:
        """Xóa dữ liệu người dùng khỏi MongoDB."""
        if not self.client:
            self.connect()
        try:
            self.collection.delete_one({"_id": user_id})
            asyncio.create_task(self.log_to_channel(f"🗑️ Deleted user data for {user_id}."))
        except ServerSelectionTimeoutError:
            asyncio.create_task(self.log_to_channel("❌ Failed to delete data, server is not available."))

    def close_connection(self) -> None:
        """Đóng kết nối MongoDB."""
        if self.client:
            self.client.close()
            asyncio.create_task(self.log_to_channel("🔌 MongoDB connection closed."))
