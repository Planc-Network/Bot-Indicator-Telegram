import ccxt
import time
from typing import Dict, List, Optional
import websocket
import json
import threading
from config.config import Config
from src.utils.logger import activity_logger, error_logger
from src.database.operations import DatabaseOps
from src.api.websocket_handler import WebSocketHandler
import requests
from .base_exchange import BaseExchange

class BitgetClient(BaseExchange):
    def __init__(self, db_session=None, use_credentials=False):
        self.db_session = db_session
        self.ws_handler = WebSocketHandler(db_session) if db_session else None
        
        # Initialize exchange with or without credentials
        if use_credentials:
            self.exchange = ccxt.bitget({
                'apiKey': Config.BITGET_API_KEY,
                'secret': Config.BITGET_SECRET,
                'password': Config.BITGET_PASSWORD,
                'enableRateLimit': True,
            })
        else:
            # Public API only
            self.exchange = ccxt.bitget({
                'enableRateLimit': True
            })
        
        self.ws = None
        self.ws_connected = False
        self.callbacks = {}
        
        self.base_url = "https://api.bitget.com/api/mix/v1/market"
    
    def retry_api_call(self, func, *args, max_retries=3, delay=1):
        """Retry mechanism for API calls"""
        for attempt in range(max_retries):
            try:
                return func(*args)
            except ccxt.NetworkError as e:
                if attempt == max_retries - 1:
                    error_logger.error(f"Network error after {max_retries} attempts: {str(e)}")
                    raise
                time.sleep(delay * (attempt + 1))
            except ccxt.ExchangeError as e:
                error_logger.error(f"Exchange error: {str(e)}")
                raise
    
    def get_ticker(self, symbol: str) -> Optional[Dict]:
        """Get current ticker information from Bitget"""
        try:
            # Format symbol for Bitget
            formatted_symbol = f"{symbol[:3]}-{symbol[3:]}" if 'USDT' in symbol else f"{symbol}-USDT"
            
            url = f"{self.base_url}/ticker"
            headers = {'Accept': 'application/json', 'User-Agent': 'Mozilla/5.0'}
            params = {'symbol': formatted_symbol}
            
            activity_logger.info(f"[Bitget] Requesting price for {formatted_symbol}")
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data:
                    ticker = data['data']
                    last_price = float(ticker['last'])
                    return {
                        'exchange': 'Bitget',
                        'symbol': symbol,
                        'last': last_price,
                        'high': float(ticker['high24h']),
                        'low': float(ticker['low24h']),
                        'volume': float(ticker['volume24h']),
                        'percentage': float(ticker['priceChangePercent']),
                        'timestamp': int(ticker['timestamp']),
                        'formatted_price': f"${last_price:,.2f}"
                    }
            
            error_logger.error(f"[Bitget] Failed to get ticker. Status: {response.status_code}")
            return None
            
        except Exception as e:
            error_logger.error(f"[Bitget] Error: {str(e)}")
            return None
    
    def get_ohlcv(self, symbol: str, timeframe: str = '1d', limit: int = 100) -> Optional[List]:
        """Get OHLCV data from Bitget"""
        try:
            # Format symbol
            formatted_symbol = f"{symbol[:3]}-{symbol[3:]}" if 'USDT' in symbol else f"{symbol}-USDT"
            
            # Map timeframe to Bitget format
            timeframe_map = {
                '1m': '1min',
                '5m': '5min',
                '15m': '15min',
                '1h': '1hour',
                '4h': '4hour',
                '1d': '1day'
            }
            period = timeframe_map.get(timeframe, '1day')
            
            # Get candle data
            url = f"{self.base_url}/market/candles"
            params = {
                'symbol': formatted_symbol,
                'period': period,
                'limit': limit
            }
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data:
                    # Convert to OHLCV format
                    return [
                        [
                            int(candle[0]),  # timestamp
                            float(candle[1]),  # open
                            float(candle[2]),  # high
                            float(candle[3]),  # low
                            float(candle[4]),  # close
                            float(candle[5])   # volume
                        ]
                        for candle in data['data']
                    ]
            
            return None
            
        except Exception as e:
            error_logger.error(f"[Bitget] Error getting OHLCV: {str(e)}")
            return None
    
    def get_order_book(self, symbol: str) -> Dict:
        """Get order book snapshot"""
        return self.retry_api_call(self.exchange.fetch_order_book, symbol)
    
    def create_order(self, symbol: str, type: str, side: str, amount: float, 
                    price: Optional[float] = None) -> Dict:
        """Create a new order"""
        return self.retry_api_call(
            self.exchange.create_order,
            symbol,
            type,
            side,
            amount,
            price
        )
    
    def setup_websocket(self, symbols: List[str], callbacks: Dict = None):
        """Setup WebSocket connection"""
        self.callbacks = callbacks or {}
        ws_url = "wss://ws.bitget.com/spot/v1/stream"
        
        def on_message(ws, message):
            data = json.loads(message)
            if 'data' in data:
                channel = data.get('channel', '')
                if channel.startswith('ticker.'):
                    self.ws_handler.handle_ohlcv(data['data'])
                elif channel.startswith('depth.'):
                    self.ws_handler.handle_order_book(data['data'])
                
                if channel in self.callbacks:
                    self.callbacks[channel](data['data'])
        
        def on_error(ws, error):
            error_logger.error(f"WebSocket error: {str(error)}")
            self.ws_connected = False
            self.ws_handler.handle_connection_error()
        
        def on_close(ws, close_status_code, close_msg):
            activity_logger.info("WebSocket connection closed")
            self.ws_connected = False
        
        def on_open(ws):
            activity_logger.info("WebSocket connection established")
            self.ws_connected = True
            # Subscribe to channels
            for symbol in symbols:
                ws.send(json.dumps({
                    "op": "subscribe",
                    "args": [
                        f"ticker.{symbol}",
                        f"trade.{symbol}",
                        f"depth.{symbol}"
                    ]
                }))
        
        self.ws = websocket.WebSocketApp(
            ws_url,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            on_open=on_open
        )
        
        ws_thread = threading.Thread(target=self.ws.run_forever)
        ws_thread.daemon = True
        ws_thread.start()

    def save_market_data(self, symbol: str):
        """Fetch and save market data"""
        try:
            # Get OHLCV
            ohlcv = self.get_ohlcv(symbol)
            DatabaseOps.save_ohlcv(self.db_session, ohlcv[-1])
            
            # Get order book
            order_book = self.get_order_book(symbol)
            DatabaseOps.save_order_book(self.db_session, order_book)
            
        except Exception as e:
            error_logger.error(f"Error saving market data: {str(e)}")

    def setup_public_websocket(self, symbols: List[str]):
        """Setup WebSocket for public data only"""
        ws_url = "wss://ws.bitget.com/spot/v1/stream"
        
        def on_message(ws, message):
            try:
                data = json.loads(message)
                if 'data' in data:
                    channel = data.get('channel', '')
                    if channel.startswith('ticker.'):
                        symbol = channel.split('.')[1]
                        ticker_data = data['data']
                        activity_logger.info(f"Received ticker for {symbol}: {ticker_data['last']}")
                        if self.ws_handler:
                            self.ws_handler.handle_ohlcv({
                                'symbol': symbol,
                                'timestamp': int(ticker_data['timestamp']),
                                'open': float(ticker_data['open24h']),
                                'high': float(ticker_data['high24h']),
                                'low': float(ticker_data['low24h']),
                                'close': float(ticker_data['last']),
                                'volume': float(ticker_data['volume24h'])
                            })
            except Exception as e:
                error_logger.error(f"Error processing message: {str(e)}")
        
        def on_error(ws, error):
            error_logger.error(f"WebSocket error: {str(error)}")
            self.ws_connected = False
            if self.ws_handler:
                self.ws_handler.handle_connection_error()
        
        def on_close(ws, close_status_code, close_msg):
            activity_logger.info("WebSocket connection closed")
            self.ws_connected = False
        
        def on_open(ws):
            activity_logger.info("WebSocket connection established")
            self.ws_connected = True
            # Subscribe to ticker channels
            subscribe_message = {
                "op": "subscribe",
                "args": [f"ticker.{symbol}" for symbol in symbols]
            }
            ws.send(json.dumps(subscribe_message))
        
        self.ws = websocket.WebSocketApp(
            ws_url,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            on_open=on_open
        )
        
        ws_thread = threading.Thread(target=self.ws.run_forever)
        ws_thread.daemon = True
        ws_thread.start()
    
    def get_public_ticker(self, symbol: str) -> Dict:
        """Get current ticker information using public API"""
        try:
            # Format symbol correctly
            formatted_symbol = f"{symbol[:3]}-{symbol[3:]}" if 'USDT' in symbol else f"{symbol}-USDT"
            
            # Use the correct Bitget API endpoint
            url = "https://api.bitget.com/api/mix/v1/market/ticker"
            
            headers = {
                'Accept': 'application/json',
                'User-Agent': 'Mozilla/5.0'
            }
            
            # Log the request
            activity_logger.info(f"Requesting price for {formatted_symbol}")
            
            # Make the request
            response = requests.get(
                url,
                params={'symbol': formatted_symbol},
                headers=headers,
                timeout=10
            )
            
            # Log the response
            activity_logger.info(f"Response status: {response.status_code}")
            activity_logger.info(f"Response body: {response.text}")
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data:
                    ticker = data['data']
                    return {
                        'symbol': symbol,
                        'last': float(ticker['last']),
                        'high': float(ticker['high24h']),
                        'low': float(ticker['low24h']),
                        'baseVolume': float(ticker['volume24h']),
                        'percentage': float(ticker['priceChangePercent']),
                        'timestamp': int(ticker['timestamp'])
                    }
            
            error_logger.error(f"Failed to get ticker. Status: {response.status_code}, Response: {response.text}")
            return None
            
        except Exception as e:
            error_logger.error(f"Error fetching price for {symbol}: {str(e)}")
            return None

    def get_exchange_name(self) -> str:
        return "Bitget"

    def get_available_pairs(self) -> List[str]:
        """Get available trading pairs from Bitget"""
        try:
            url = f"{self.base_url}/market/tickers"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data:
                    return [ticker['symbol'].replace('-', '') for ticker in data['data']]
            
            return []
        except Exception as e:
            error_logger.error(f"[Bitget] Error getting pairs: {str(e)}")
            return [] 