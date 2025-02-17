from sqlalchemy.orm import Session
from .models import OHLCV, User, Trade, Signal, OrderBook
from datetime import datetime
import json

class DatabaseOps:
    @staticmethod
    def save_ohlcv(session: Session, data: dict):
        """Save OHLCV data to database"""
        try:
            ohlcv = OHLCV(
                symbol=data['symbol'],
                timestamp=datetime.fromtimestamp(data['timestamp']/1000),
                open=data['open'],
                high=data['high'],
                low=data['low'],
                close=data['close'],
                volume=data['volume']
            )
            session.add(ohlcv)
            session.commit()
            activity_logger.info(f"Saved OHLCV data for {data['symbol']}")
        except Exception as e:
            session.rollback()
            error_logger.error(f"Error saving OHLCV data: {str(e)}")
            raise
    
    @staticmethod
    def save_order_book(session: Session, data: dict):
        """Save order book snapshot"""
        try:
            order_book = OrderBook(
                symbol=data['symbol'],
                timestamp=datetime.fromtimestamp(data['timestamp']/1000) if 'timestamp' in data else datetime.utcnow(),
                bids=json.dumps(data['bids']),
                asks=json.dumps(data['asks'])
            )
            session.add(order_book)
            session.commit()
            activity_logger.info(f"Saved order book for {data['symbol']}")
        except Exception as e:
            session.rollback()
            error_logger.error(f"Error saving order book: {str(e)}")
            raise 