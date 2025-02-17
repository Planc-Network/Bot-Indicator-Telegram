from typing import Dict
import requests
from src.utils.logger import activity_logger, error_logger
import time

class CryptoClient:
    def __init__(self):
        self.base_url = "https://indodax.com/api"
        
    def get_public_ticker(self, symbol: str) -> Dict:
        """Get current ticker information using Indodax API"""
        try:
            # Format symbol untuk Indodax (btcidr format)
            formatted_symbol = f"{symbol[:3].lower()}idr"
            
            # Get ticker data
            url = f"{self.base_url}/ticker/{formatted_symbol}"
            
            activity_logger.info(f"Requesting price for {formatted_symbol}")
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                ticker = data['ticker']
                
                # Convert string values to float
                last_price = float(ticker['last'])
                high_price = float(ticker['high'])
                low_price = float(ticker['low'])
                volume = float(ticker['vol_' + symbol[:3].lower()])
                
                # Calculate 24h change percentage
                open_price = float(ticker.get('open', last_price))
                if open_price > 0:
                    change_percent = ((last_price - open_price) / open_price) * 100
                else:
                    change_percent = 0.0
                
                return {
                    'symbol': symbol,
                    'last': last_price,
                    'high': high_price,
                    'low': low_price,
                    'baseVolume': volume,
                    'percentage': change_percent,
                    'timestamp': int(ticker['server_time']),
                    'idr_price': f"Rp {last_price:,.0f}"  # Format IDR price
                }
            
            error_logger.error(f"Failed to get ticker. Status: {response.status_code}, Response: {response.text}")
            return None
            
        except Exception as e:
            error_logger.error(f"Error fetching price for {symbol}: {str(e)}")
            return None
    
    def get_all_tickers(self) -> Dict:
        """Get all available tickers from Indodax"""
        try:
            url = f"{self.base_url}/ticker_all"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            return None
            
        except Exception as e:
            error_logger.error(f"Error fetching all tickers: {str(e)}")
            return None 