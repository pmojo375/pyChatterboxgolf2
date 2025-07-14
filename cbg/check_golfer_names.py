#!/usr/bin/env python
import os
import sys
import django
import sqlite3

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cbg.settings')
django.setup()

from main.models import *

def check_golfer_names():
    """
    Check for golfers in old database that don't exist in new database
    """
    print("Checking golfer names between old and new databases...")
    
    # Connect to old database
    try:
        conn_old = sqlite3.connect('./old.sqlite3')
        print("✓ Connected to old database")
    except Exception as e:
        print(f"✗ Error connecting to old database: {e}")
        return
    
    try:
        # Get all golfers from old database for 2025
        cursor = conn_old.execute("SELECT DISTINCT golfer FROM main_gameentry WHERE year = 2025")
        old_golfer_ids = [row[0] for row in cursor]
        
        print(f"\nFound {len(old_golfer_ids)} unique golfer IDs in old database for 2025")
        
        # Get golfer names from old database
        old_golfer_names = []
        for golfer_id in old_golfer_ids:
            cursor = conn_old.execute("SELECT name FROM main_golfer WHERE id = ?", (golfer_id,))
            result = cursor.fetchone()
            if result:
                old_golfer_names.append(result[0])
        
        print(f"Old database golfer names: {sorted(old_golfer_names)}")
        
        # Get all golfers from new database
        new_golfers = Golfer.objects.all()
        new_golfer_names = [golfer.name for golfer in new_golfers]
        
        print(f"\nNew database golfer names: {sorted(new_golfer_names)}")
        
        # Find missing golfers
        missing_golfers = []
        for old_name in old_golfer_names:
            if old_name not in new_golfer_names:
                missing_golfers.append(old_name)
        
        print(f"\nMissing golfers: {missing_golfers}")
        
        # Check for case-insensitive matches
        print(f"\nChecking for case-insensitive matches...")
        for old_name in missing_golfers:
            for new_name in new_golfer_names:
                if old_name.lower() == new_name.lower():
                    print(f"  Case mismatch found: '{old_name}' (old) vs '{new_name}' (new)")
        
        # Check for exact matches in game entries
        print(f"\nChecking game entries for missing golfers...")
        cursor = conn_old.execute("""
            SELECT DISTINCT g.name, ge.week, ge.won 
            FROM main_gameentry ge 
            JOIN main_golfer g ON ge.golfer = g.id 
            WHERE ge.year = 2025 AND g.name NOT IN (
                SELECT name FROM main_golfer WHERE id IN (
                    SELECT DISTINCT golfer FROM main_gameentry WHERE year = 2025
                )
            )
        """)
        
        missing_entries = cursor.fetchall()
        if missing_entries:
            print(f"Game entries for missing golfers:")
            for name, week, won in missing_entries:
                print(f"  {name} - Week {week} - {'Winner' if won else 'Loser'}")
        
    except Exception as e:
        print(f"✗ Error during check: {e}")
    finally:
        conn_old.close()
        print("\n✓ Database connection closed")

if __name__ == "__main__":
    check_golfer_names() 