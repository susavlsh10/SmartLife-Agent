#!/usr/bin/env python3
"""
Migration script to add 'plan' column to projects table
"""
import sqlite3
import os

# Get the database path
db_path = os.path.join(os.path.dirname(__file__), "smartlife.db")

def add_plan_column():
    """Add plan column to projects table if it doesn't exist"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if column exists
        cursor.execute("PRAGMA table_info(projects)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'plan' not in columns:
            print("Adding 'plan' column to projects table...")
            cursor.execute("ALTER TABLE projects ADD COLUMN plan TEXT")
            conn.commit()
            print("✓ Successfully added 'plan' column")
        else:
            print("'plan' column already exists")
            
    except Exception as e:
        print(f"Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    add_plan_column()
