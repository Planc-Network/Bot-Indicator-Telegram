from typing import Dict, List
from .indodax_client import IndodaxClient
from .bitget_client import BitgetClient
from src.utils.logger import activity_logger, error_logger

class PriceService:
    def __init__(self):
        self.exchanges = {
            'indodax': IndodaxClient(),
            'bitget': BitgetClient()
        }
    
    def get_price(self, symbol: str, exchange: str = None) -> Dict:
        """Get price from specific exchange or all exchanges"""
        results = {}
        
        if exchange and exchange in self.exchanges:
            # Get price from specific exchange
            ticker = self.exchanges[exchange].get_ticker(symbol)
            if ticker:
                results[exchange] = ticker
        else:
            # Get price from all exchanges
            for name, client in self.exchanges.items():
                ticker = client.get_ticker(symbol)
                if ticker:
                    results[name] = ticker
        
        return results
    
    def format_price_message(self, prices: Dict) -> str:
        """Format price data into readable message"""
        if not prices:
            return "❌ Could not fetch prices from any exchange"
            
        message = "💰 *Price Comparison*\n\n"
        for exchange, data in prices.items():
            message += (
                f"*{exchange.upper()}*\n"
                f"Price: {data['formatted_price']}\n"
                f"24h High: {data['high']:,.2f}\n"
                f"24h Low: {data['low']:,.2f}\n"
                f"24h Change: {data['percentage']:+.2f}%\n"
                f"Volume: {data['volume']:.2f}\n\n"
            )
        
        return message 

    def get_available_pairs(self, exchange: str = None) -> Dict[str, List[str]]:
        """Get available pairs from exchanges"""
        pairs = {}
        
        if exchange and exchange in self.exchanges:
            pairs[exchange] = self.exchanges[exchange].get_available_pairs()
        else:
            for name, client in self.exchanges.items():
                pairs[name] = client.get_available_pairs()
            
        return pairs

    def format_pairs_message(self, pairs: Dict[str, List[str]]) -> str:
        """Format available pairs into readable message"""
        message = "📊 *Available Trading Pairs*\n\n"
        
        for exchange, symbols in pairs.items():
            message += f"*{exchange.upper()}*\n"
            # Group by quote currency (USDT, IDR, etc)
            by_quote = {}
            for symbol in symbols:
                quote = symbol[-4:] if symbol.endswith(('USDT', 'BUSD')) else symbol[-3:]
                if quote not in by_quote:
                    by_quote[quote] = []
                by_quote[quote].append(symbol[:-len(quote)])
            
            for quote, bases in by_quote.items():
                message += f"{quote}: {', '.join(bases)}\n"
            message += "\n"
        
        return message 

    def get_ohlcv(self, symbol: str, timeframe: str = '1d', exchange: str = None) -> List:
        """Get OHLCV data from exchange"""
        try:
            # Default to first available exchange if none specified
            if exchange and exchange in self.exchanges:
                client = self.exchanges[exchange]
            else:
                # Try Indodax first, then Bitget
                for name, client in self.exchanges.items():
                    data = client.get_ohlcv(symbol, timeframe)
                    if data:
                        return data
                return None
            
            return client.get_ohlcv(symbol, timeframe)
        
        except Exception as e:
            error_logger.error(f"Error getting OHLCV data: {str(e)}")
            return None 