"""
MongoDB Database Connection and Configuration
Async MongoDB client using Motor for non-blocking I/O
"""

import dns.resolver

# Configure DNS to use Google DNS (bypass local DNS issues)
# MUST BE DONE BEFORE IMPORTING MOTOR/PYMONGO
# try:
#     dns.resolver.default_resolver = dns.resolver.Resolver(configure=False)
#     dns.resolver.default_resolver.nameservers = ['8.8.8.8']
# except Exception as e:
#     print(f"Warning: Could not configure custom DNS resolver: {e}")

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure
import structlog
from typing import Optional

logger = structlog.get_logger(__name__)


class MongoDB:
    """MongoDB connection manager"""
    
    client: Optional[AsyncIOMotorClient] = None
    db = None
    _connected: bool = False
    
    @classmethod
    async def connect(cls):
        """Initialize MongoDB connection"""
        try:
            from app.config import settings
            mongodb_url = settings.mongodb_url
            db_name = settings.mongodb_db
            
            cls.client = AsyncIOMotorClient(
                mongodb_url,
                maxPoolSize=10,
                minPoolSize=1,
                serverSelectionTimeoutMS=2000,
                connectTimeoutMS=2000,
                socketTimeoutMS=2000
            )
            
            # Verify connection with timeout
            # If this fails, we catch exception below and continue without DB
            await cls.client.admin.command('ping')
            
            cls.db = cls.client[db_name]
            cls._connected = True
            
            logger.info("mongodb.connected", 
                       url=mongodb_url.split('@')[-1],  # Hide credentials
                       database=db_name)
            
            # Create indexes
            await cls._create_indexes()
            
        except ConnectionFailure as e:
            logger.warning("mongodb.connection_failed", error=str(e))
            cls._connected = False
            # Don't raise - allow server to start without MongoDB
        except Exception as e:
            logger.warning("mongodb.setup_failed", error=str(e))
            cls._connected = False
            # Don't raise - allow server to start without MongoDB
    
    @classmethod
    async def _create_indexes(cls):
        """Create database indexes for optimal queries"""
        if cls.db is None:
            return
        
        try:
            detections = cls.db.detections
            await detections.create_index("timestamp", name="idx_timestamp")
            await detections.create_index("detection_type", name="idx_type")
            await detections.create_index([("timestamp", -1)], name="idx_timestamp_desc")
            logger.info("mongodb.indexes_created")
        except Exception as e:
            logger.warning("mongodb.index_creation_failed", error=str(e))
    
    @classmethod
    async def close(cls):
        """Close MongoDB connection"""
        if cls.client:
            cls.client.close()
            cls._connected = False
            logger.info("mongodb.disconnected")
    
    @classmethod
    async def health_check(cls) -> bool:
        """Check if MongoDB is healthy"""
        try:
            if cls.client and cls._connected:
                await cls.client.admin.command('ping')
                return True
            return False
        except Exception as e:
            logger.error("mongodb.health_check_failed", error=str(e))
            return False
    
    @classmethod
    def get_collection(cls, name: str):
        """Get a collection by name"""
        if cls.db is None:
            raise RuntimeError("MongoDB not connected. Check your MONGODB_URL in .env")
        return cls.db[name]
    
    @classmethod
    def is_connected(cls) -> bool:
        """Check if MongoDB is connected"""
        return cls._connected


# Singleton instance
mongodb = MongoDB()
