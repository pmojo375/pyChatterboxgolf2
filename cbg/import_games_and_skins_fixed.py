#!/usr/bin/env python
import os
import sys
import django
import sqlite3

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cbg.settings')
django.setup()

from main.models import *
from django.utils import timezone

def get_or_create_golfer(golfer_name):
    """
    Get or create a golfer, handling case sensitivity issues
    """
    # First try exact match
    try:
        return Golfer.objects.get(name=golfer_name)
    except Golfer.DoesNotExist:
        pass
    
    # Try case-insensitive match
    try:
        return Golfer.objects.get(name__iexact=golfer_name)
    except Golfer.DoesNotExist:
        pass
    
    # Create new golfer if not found
    golfer = Golfer.objects.create(name=golfer_name)
    print(f"  ✓ Created new golfer: {golfer_name}")
    return golfer

def import_games_and_skins_for_current_season():
    """
    Import games, game entries, and skin entries from old database for current season (2025)
    Handles case sensitivity issues and creates missing golfers
    """
    current_year = 2025
    
    print(f"Starting import for season {current_year}...")
    
    # Connect to old database
    try:
        conn_old = sqlite3.connect('./old.sqlite3')
        print("✓ Connected to old database")
    except Exception as e:
        print(f"✗ Error connecting to old database: {e}")
        return
    
    try:
        # Get current season
        season, created = Season.objects.get_or_create(year=current_year)
        if created:
            print(f"✓ Created season {current_year}")
        else:
            print(f"✓ Using existing season {current_year}")
        
        # Import Games (skip if already exists)
        print("\n--- Importing Games ---")
        cursor = conn_old.execute("SELECT name, desc, week, year from main_game WHERE year = ?", (current_year,))
        games_imported = 0
        
        for row in cursor:
            name, desc, week_num, year = row
            
            # Check if week exists in new database
            try:
                week_obj = Week.objects.get(season=season, number=week_num, rained_out=False)
                
                # Check if game already exists for this week
                if not Game.objects.filter(week=week_obj).exists():
                    game = Game(name=name, desc=desc, week=week_obj)
                    game.save()
                    games_imported += 1
                    print(f"  ✓ Imported game: {name} (Week {week_num})")
                else:
                    print(f"  - Game already exists for Week {week_num}")
                    
            except Week.DoesNotExist:
                print(f"  ✗ Week {week_num} not found in new database")
        
        print(f"Total games imported: {games_imported}")
        
        # Import Game Entries
        print("\n--- Importing Game Entries ---")
        cursor = conn_old.execute("SELECT golfer, week, won, year from main_gameentry WHERE year = ?", (current_year,))
        game_entries_imported = 0
        
        for row in cursor:
            golfer_id, week_num, won, year = row
            
            try:
                # Get golfer name from old database
                golfer_cursor = conn_old.execute("SELECT name from main_golfer WHERE id = ?", (golfer_id,))
                golfer_name = golfer_cursor.fetchone()[0]
                
                # Get or create golfer (handles case sensitivity)
                golfer_obj = get_or_create_golfer(golfer_name)
                week_obj = Week.objects.get(season=season, number=week_num, rained_out=False)
                game_obj = Game.objects.get(week=week_obj)
                
                # Check if entry already exists
                if not GameEntry.objects.filter(golfer=golfer_obj, game=game_obj, week=week_obj).exists():
                    game_entry = GameEntry(
                        golfer=golfer_obj,
                        game=game_obj,
                        week=week_obj,
                        winner=bool(won)
                    )
                    game_entry.save()
                    game_entries_imported += 1
                    print(f"  ✓ Imported game entry: {golfer_name} - {'Winner' if won else 'Loser'} (Week {week_num})")
                else:
                    print(f"  - Game entry already exists for {golfer_name} (Week {week_num})")
                    
            except (Week.DoesNotExist, Game.DoesNotExist) as e:
                print(f"  ✗ Error importing game entry: {e}")
        
        print(f"Total game entries imported: {game_entries_imported}")
        
        # Import Skin Entries
        print("\n--- Importing Skin Entries ---")
        cursor = conn_old.execute("SELECT golfer, week, year from main_skinentry WHERE year = ?", (current_year,))
        skin_entries_imported = 0
        
        for row in cursor:
            golfer_id, week_num, year = row
            
            try:
                # Get golfer name from old database
                golfer_cursor = conn_old.execute("SELECT name from main_golfer WHERE id = ?", (golfer_id,))
                golfer_name = golfer_cursor.fetchone()[0]
                
                # Get or create golfer (handles case sensitivity)
                golfer_obj = get_or_create_golfer(golfer_name)
                week_obj = Week.objects.get(season=season, number=week_num, rained_out=False)
                
                # Check if entry already exists
                if not SkinEntry.objects.filter(golfer=golfer_obj, week=week_obj).exists():
                    skin_entry = SkinEntry(
                        golfer=golfer_obj,
                        week=week_obj,
                        winner=False  # Will be calculated later
                    )
                    skin_entry.save()
                    skin_entries_imported += 1
                    print(f"  ✓ Imported skin entry: {golfer_name} (Week {week_num})")
                else:
                    print(f"  - Skin entry already exists for {golfer_name} (Week {week_num})")
                    
            except Week.DoesNotExist as e:
                print(f"  ✗ Error importing skin entry: {e}")
        
        print(f"Total skin entries imported: {skin_entries_imported}")
        
        # Summary
        print(f"\n📊 Import Summary for Season {current_year}:")
        print(f"  Games: {games_imported}")
        print(f"  Game Entries: {game_entries_imported}")
        print(f"  Skin Entries: {skin_entries_imported}")
        
    except Exception as e:
        print(f"✗ Error during import: {e}")
    finally:
        conn_old.close()
        print("\n✓ Database connection closed")

if __name__ == "__main__":
    import_games_and_skins_for_current_season() 