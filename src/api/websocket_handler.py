from src.database.operations import DatabaseOps
from src.utils.logger import activity_logger, error_logger
from src.utils.admin_notifier import AdminNotifier
import asyncio

class WebSocketHandler:
    def __init__(self, db_session):
        self.db_session = db_session
        self.admin_notifier = AdminNotifier()
        self.reconnect_delay = 1  # Mulai dengan 1 detik
        self.max_reconnect_delay = 300  # Maksimum 5 menit
    
    def handle_ohlcv(self, data):
        """Handle OHLCV data from WebSocket"""
        try:
            DatabaseOps.save_ohlcv(self.db_session, data)
            self.reconnect_delay = 1  # Reset delay setelah sukses
        except Exception as e:
            error_msg = f"Error saving OHLCV data: {str(e)}"
            error_logger.error(error_msg)
            asyncio.create_task(self.admin_notifier.notify_error(error_msg))
    
    def handle_order_book(self, data):
        """Handle order book data from WebSocket"""
        try:
            DatabaseOps.save_order_book(self.db_session, data)
            self.reconnect_delay = 1  # Reset delay setelah sukses
        except Exception as e:
            error_msg = f"Error saving order book data: {str(e)}"
            error_logger.error(error_msg)
            asyncio.create_task(self.admin_notifier.notify_error(error_msg))
    
    def handle_connection_error(self):
        """Handle WebSocket connection errors"""
        error_msg = f"WebSocket connection lost. Reconnecting in {self.reconnect_delay} seconds..."
        error_logger.warning(error_msg)
        asyncio.create_task(self.admin_notifier.notify_error(error_msg))
        
        # Exponential backoff
        asyncio.sleep(self.reconnect_delay)
        self.reconnect_delay = min(self.reconnect_delay * 2, self.max_reconnect_delay) 