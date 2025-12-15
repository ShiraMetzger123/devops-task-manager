#!/usr/bin/env python3
"""
Database migration script to add new columns to existing tasks table.
Run this script if you have existing data you want to keep.
"""

import os
import sqlite3
from datetime import datetime

def migrate_database():
    db_path = 'instance/tasks.db'
    
    if not os.path.exists(db_path):
        print("No existing database found. New database will be created automatically.")
        return
    
    print("Migrating existing database...")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if tasks table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tasks'")
        if not cursor.fetchone():
            print("No tasks table found. New schema will be created automatically.")
            conn.close()
            return
        
        # Check existing columns
        cursor.execute("PRAGMA table_info(tasks)")
        columns = [column[1] for column in cursor.fetchall()]
        print(f"Current columns: {columns}")
        
        migrations = []
        
        if 'priority' not in columns:
            migrations.append("ALTER TABLE tasks ADD COLUMN priority VARCHAR(20) DEFAULT 'medium'")
        
        if 'category' not in columns:
            migrations.append("ALTER TABLE tasks ADD COLUMN category VARCHAR(50) DEFAULT 'general'")
        
        if 'updated_at' not in columns:
            migrations.append("ALTER TABLE tasks ADD COLUMN updated_at DATETIME")
        
        if 'completed_at' not in columns:
            migrations.append("ALTER TABLE tasks ADD COLUMN completed_at DATETIME")
        
        if 'group_name' not in columns:
            migrations.append("ALTER TABLE tasks ADD COLUMN group_name VARCHAR(100) DEFAULT 'default'")
        
        if migrations:
            for migration in migrations:
                print(f"Executing: {migration}")
                cursor.execute(migration)
            
            # Set default values for existing records
            cursor.execute("UPDATE tasks SET priority = 'medium' WHERE priority IS NULL")
            cursor.execute("UPDATE tasks SET category = 'general' WHERE category IS NULL")
            cursor.execute("UPDATE tasks SET updated_at = created_at WHERE updated_at IS NULL")
            cursor.execute("UPDATE tasks SET group_name = 'default' WHERE group_name IS NULL")
            
            conn.commit()
            print("Migration completed successfully!")
        else:
            print("Database is already up to date.")
            
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    migrate_database()