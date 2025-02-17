from abc import ABC, abstractmethod
from typing import Dict, Optional, List

class BaseExchange(ABC):
    @abstractmethod
    def get_ticker(self, symbol: str) -> Optional[Dict]:
        """Get ticker information for a symbol"""
        pass
    
    @abstractmethod
    def get_exchange_name(self) -> str:
        """Get exchange name"""
        pass
        
    @abstractmethod
    def get_available_pairs(self) -> List[str]:
        """Get list of available trading pairs"""
        pass 