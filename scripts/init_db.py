#!/usr/bin/env python
"""Initialize database tables."""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import init_db, engine
from models.rating import Rating


def main():
    """Initialize database tables."""
    print("Initializing database tables...")
    
    try:
        init_db()
        print("✓ Database tables created successfully")
        
        # Print created tables
        from sqlalchemy import inspect
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"\nCreated tables: {', '.join(tables)}")
        
    except Exception as e:
        print(f"✗ Error initializing database: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
