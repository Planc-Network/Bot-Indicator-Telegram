from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Enum, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()

class UserRole(enum.Enum):
    FREE = "free"
    PREMIUM = "premium"
    ADMIN = "admin"

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(String, unique=True)
    username = Column(String)
    role = Column(Enum(UserRole), default=UserRole.FREE)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    subscription_end = Column(DateTime, nullable=True)
    
    signals = relationship("Signal", back_populates="user")
    trades = relationship("Trade", back_populates="user")

class OHLCV(Base):
    __tablename__ = 'ohlcv'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String)
    timestamp = Column(DateTime)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)
    
    class Config:
        indexes = [
            ('symbol', 'timestamp')
        ]

class Signal(Base):
    __tablename__ = 'signals'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    symbol = Column(String)
    direction = Column(String)  # 'long' or 'short'
    entry_price = Column(Float)
    stop_loss = Column(Float)
    take_profit = Column(Float)
    confidence = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String)  # 'pending', 'executed', 'cancelled', 'completed'
    
    user = relationship("User", back_populates="signals")

class Trade(Base):
    __tablename__ = 'trades'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    signal_id = Column(Integer, ForeignKey('signals.id'), nullable=True)
    symbol = Column(String)
    direction = Column(String)
    entry_price = Column(Float)
    exit_price = Column(Float, nullable=True)
    quantity = Column(Float)
    pnl = Column(Float, nullable=True)
    status = Column(String)  # 'open', 'closed'
    opened_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)
    
    user = relationship("User", back_populates="trades")

class OrderBook(Base):
    __tablename__ = 'order_books'
    
    id = Column(Integer, primary_key=True)
    symbol = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    bids = Column(JSON)  # Menyimpan bids dalam format JSON
    asks = Column(JSON)  # Menyimpan asks dalam format JSON
    
    class Config:
        indexes = [
            ('symbol', 'timestamp')
        ] 