#!/usr/bin/env python3
"""
Database migration script to add due_date column to todo_items table
"""
import sys
import os

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from app.database import engine


def add_todo_due_date_column():
    """Add due_date column to todo_items table"""
    with engine.connect() as conn:
        try:
            # Check if column already exists
            result = conn.execute(text(
                "SELECT COUNT(*) FROM pragma_table_info('todo_items') WHERE name='due_date'"
            ))
            count = result.scalar()
            
            if count > 0:
                print("✅ due_date column already exists in todo_items table")
                return
            
            # Add the column
            conn.execute(text(
                "ALTER TABLE todo_items ADD COLUMN due_date TIMESTAMP NULL"
            ))
            conn.commit()
            print("✅ Successfully added due_date column to todo_items table")
            
        except Exception as e:
            print(f"❌ Error adding due_date column: {e}")
            conn.rollback()
            raise


if __name__ == "__main__":
    print("Adding due_date column to todo_items table...")
    add_todo_due_date_column()
    print("Migration complete!")
