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
    print("Initializing database...")
    print(f"Database URL: {engine.url}")
    
    try:
        # Import all models to ensure they're registered with Base
        from models import rating
        
        # Create all tables
        init_db()
        
        print("✓ Database tables created successfully!")
        print("\nCreated tables:")
        print("  - ratings")
        
    except Exception as e:
        print(f"✗ Error initializing database: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
