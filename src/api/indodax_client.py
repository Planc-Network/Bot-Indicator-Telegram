from typing import Dict, Optional, List
import requests
from src.utils.logger import activity_logger, error_logger
from .base_exchange import BaseExchange
import pandas as pd

class IndodaxClient(BaseExchange):
    def __init__(self):
        self.base_url = "https://indodax.com/api"
        
    def get_exchange_name(self) -> str:
        return "Indodax"
        
    def get_ticker(self, symbol: str) -> Optional[Dict]:
        """Get current ticker information from Indodax"""
        try:
            # Format symbol untuk Indodax (btcidr format)
            formatted_symbol = f"{symbol[:3].lower()}idr"
            
            url = f"{self.base_url}/ticker/{formatted_symbol}"
            activity_logger.info(f"[Indodax] Requesting price for {formatted_symbol}")
            
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                ticker = data['ticker']
                
                last_price = float(ticker['last'])
                return {
                    'exchange': 'Indodax',
                    'symbol': symbol,
                    'last': last_price,
                    'high': float(ticker['high']),
                    'low': float(ticker['low']),
                    'volume': float(ticker['vol_' + symbol[:3].lower()]),
                    'percentage': self._calculate_change(last_price, ticker.get('open', last_price)),
                    'timestamp': int(ticker['server_time']),
                    'formatted_price': f"Rp {last_price:,.0f}"
                }
            
            error_logger.error(f"[Indodax] Failed to get ticker. Status: {response.status_code}")
            return None
            
        except Exception as e:
            error_logger.error(f"[Indodax] Error: {str(e)}")
            return None
            
    def _calculate_change(self, current: float, open_price: float) -> float:
        """Calculate price change percentage"""
        if float(open_price) > 0:
            return ((float(current) - float(open_price)) / float(open_price)) * 100
        return 0.0

    def get_available_pairs(self) -> List[str]:
        """Get available trading pairs from Indodax"""
        try:
            url = f"{self.base_url}/pairs"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                pairs = response.json()
                return [pair['symbol'].upper() for pair in pairs]
            
            return []
        except Exception as e:
            error_logger.error(f"[Indodax] Error getting pairs: {str(e)}")
            return []

    def get_ohlcv(self, symbol: str, timeframe: str = '1d') -> Optional[List]:
        """Get OHLCV data from Indodax"""
        try:
            # Format symbol
            formatted_symbol = f"{symbol[:3].lower()}idr"
            
            # Get trades data
            url = f"{self.base_url}/trades/{formatted_symbol}"
            activity_logger.info(f"Fetching trades from: {url}")
            
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                trades = response.json()
                activity_logger.info(f"Received {len(trades)} trades")
                
                if not trades:
                    return None
                    
                # Convert trades to DataFrame
                df = pd.DataFrame(trades)
                df['date'] = pd.to_datetime(df['date'].astype(float), unit='s')
                df['price'] = df['price'].astype(float)
                df['amount'] = df['amount'].astype(float)
                df.set_index('date', inplace=True)
                
                # Sort by date
                df = df.sort_index()
                
                # Resample based on timeframe
                timeframe_map = {
                    '1m': '1min',
                    '5m': '5min',
                    '15m': '15min',
                    '1h': '1h',
                    '4h': '4h',
                    '1d': '1d'
                }
                period = timeframe_map.get(timeframe, '1d')
                
                # Create OHLCV data
                ohlcv = pd.DataFrame()
                ohlcv['open'] = df['price'].resample(period).first()
                ohlcv['high'] = df['price'].resample(period).max()
                ohlcv['low'] = df['price'].resample(period).min()
                ohlcv['close'] = df['price'].resample(period).last()
                ohlcv['volume'] = df['amount'].resample(period).sum()
                
                # Fill missing data
                ohlcv = ohlcv.fillna(method='ffill')
                
                # Convert to list format
                result = [
                    [int(t.timestamp() * 1000), row.open, row.high, row.low, row.close, row.volume]
                    for t, row in ohlcv.iterrows()
                    if not pd.isna(row.open)  # Skip any remaining NaN values
                ]
                
                activity_logger.info(f"Generated {len(result)} OHLCV candles")
                return result
                
            return None
            
        except Exception as e:
            error_logger.error(f"[Indodax] Error getting OHLCV: {str(e)}")
            return None 