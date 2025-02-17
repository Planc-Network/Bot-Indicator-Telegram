import redis
import json
from config.config import Config
from src.utils.logger import error_logger

class CacheManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CacheManager, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        try:
            self.redis = redis.from_url(Config.REDIS_URL)
        except redis.ConnectionError as e:
            error_logger.error(f"Redis connection error: {str(e)}")
            self.redis = None
    
    def set_data(self, key: str, value: any, expiry: int = 3600):
        """Store data in cache with expiry in seconds"""
        try:
            if self.redis:
                self.redis.setex(
                    key,
                    expiry,
                    json.dumps(value)
                )
        except Exception as e:
            error_logger.error(f"Cache set error: {str(e)}")
    
    def get_data(self, key: str):
        """Retrieve data from cache"""
        try:
            if self.redis:
                data = self.redis.get(key)
                return json.loads(data) if data else None
        except Exception as e:
            error_logger.error(f"Cache get error: {str(e)}")
            return None 