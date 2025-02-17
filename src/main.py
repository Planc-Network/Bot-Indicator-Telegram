from src.bot.telegram_bot import TradingBot
from src.database.connection import DatabaseManager
from src.utils.logger import activity_logger, error_logger
from src.utils.admin_notifier import AdminNotifier
import asyncio
import platform
import signal

async def main():
    """Main function to run the bot"""
    bot = None
    
    try:
        activity_logger.info("Initializing bot...")
        
        # Initialize database
        db = DatabaseManager()
        db.create_tables()
        activity_logger.info("Database initialized")
        
        # Initialize bot
        bot = TradingBot()
        activity_logger.info("Bot instance created")
        
        # Set up signal handlers if not on Windows
        if platform.system() != 'Windows':
            def signal_handler():
                if bot and hasattr(bot.app, 'running') and bot.app.running:
                    asyncio.create_task(bot.app.stop())
            
            loop = asyncio.get_event_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, signal_handler)
            activity_logger.info("Signal handlers set up")
        
        # Run the bot
        activity_logger.info("Starting bot...")
        await bot.run()
        
    except KeyboardInterrupt:
        activity_logger.info("Received keyboard interrupt")
    except Exception as e:
        error_logger.error(f"Bot error: {str(e)}", exc_info=True)
    finally:
        if bot:
            try:
                activity_logger.info("Attempting to stop bot...")
                if hasattr(bot.app, 'running') and bot.app.running:
                    await bot.app.stop()
                activity_logger.info("Bot stopped successfully")
            except Exception as e:
                error_logger.error(f"Error stopping bot: {str(e)}", exc_info=True)
        
        activity_logger.info("Bot shutdown complete")

def run_bot():
    """Run the bot with proper asyncio handling"""
    try:
        activity_logger.info("Starting bot process")
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except Exception as e:
        error_logger.error(f"Fatal error: {str(e)}", exc_info=True)
        print(f"Bot stopped due to error: {str(e)}")

if __name__ == "__main__":
    run_bot() 