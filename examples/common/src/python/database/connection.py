"""Database connection utilities"""

import os
from typing import Optional

from sqlalchemy import create_engine, Engine


class DatabaseConnection:
    """Database connection manager"""
    
    def __init__(self):
        self._engine: Optional[Engine] = None
    
    def get_engine(self) -> Engine:
        """Get database engine (singleton pattern).
        
        Returns:
            SQLAlchemy engine
        """
        if self._engine is None:
            database_url = os.environ.get("DATABASE_URL")
            if not database_url:
                raise ValueError("DATABASE_URL environment variable not set")
            
            self._engine = create_engine(
                database_url,
                pool_size=1,  # Lambda-optimized
                max_overflow=0,
                pool_pre_ping=True,
                pool_recycle=3600
            )
        
        return self._engine


# Global instance
db_connection = DatabaseConnection()