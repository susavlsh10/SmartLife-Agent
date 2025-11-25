#!/usr/bin/env python3
"""
Database migration script to add calendar_event_id column to todo_items table
"""
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from app.database import engine


def add_calendar_event_id_column():
    """Add calendar_event_id column to todo_items table"""
    with engine.connect() as conn:
        try:
            # Check if column already exists
            result = conn.execute(text(
                "SELECT COUNT(*) FROM pragma_table_info('todo_items') WHERE name='calendar_event_id'"
            ))
            count = result.scalar()
            
            if count > 0:
                print("✅ calendar_event_id column already exists in todo_items table")
                return
            
            # Add the column
            conn.execute(text(
                "ALTER TABLE todo_items ADD COLUMN calendar_event_id TEXT NULL"
            ))
            conn.commit()
            print("✅ Successfully added calendar_event_id column to todo_items table")
            
        except Exception as e:
            print(f"❌ Error adding calendar_event_id column: {e}")
            conn.rollback()
            raise


if __name__ == "__main__":
    print("Adding calendar_event_id column to todo_items table...")
    add_calendar_event_id_column()
    print("Migration complete!")
