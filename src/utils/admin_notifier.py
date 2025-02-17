from telegram import Bot
from config.config import Config

class AdminNotifier:
    def __init__(self):
        self.bot = Bot(token=Config.TELEGRAM_BOT_TOKEN)
    
    async def notify_error(self, error_message: str):
        """Send error notification to admin"""
        try:
            await self.bot.send_message(
                chat_id=Config.TELEGRAM_ADMIN_ID,
                text=f"❌ *Error Alert*\n\n{error_message}",
                parse_mode='Markdown'
            )
        except Exception as e:
            # Log to file since we can't notify admin
            error_logger.critical(f"Failed to notify admin: {str(e)}") 