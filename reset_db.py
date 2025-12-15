#!/usr/bin/env python3
"""
Database reset script - deletes existing database and creates fresh schema.
WARNING: This will delete all existing data!
"""

import os

def reset_database():
    db_path = 'instance/tasks.db'
    
    if os.path.exists(db_path):
        print(f"Deleting existing database: {db_path}")
        os.remove(db_path)
        print("Database deleted successfully!")
    else:
        print("No existing database found.")
    
    print("New database will be created automatically when you run the app.")

if __name__ == '__main__':
    confirm = input("This will DELETE ALL existing data. Are you sure? (yes/no): ")
    if confirm.lower() == 'yes':
        reset_database()
    else:
        print("Reset cancelled.")