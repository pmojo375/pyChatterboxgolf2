#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cbg.cbg.settings')
django.setup()

from main.models import Week, Season, SkinEntry
from main.views import calculate_skin_winners

# Get current season and Week 1
current_season = Season.objects.latest('year')
week = Week.objects.get(number=1, season=current_season)

print(f"Current season: {current_season.year}")
print(f"Week 1: {week}")

# Check skin entries
skin_entries = SkinEntry.objects.filter(week=week)
print(f"\nSkin entries count: {skin_entries.count()}")
for entry in skin_entries:
    print(f"  - {entry.golfer.name}")

# Check skin winners
winners = calculate_skin_winners(week)
print(f"\nSkin winners count: {len(winners)}")
for winner in winners:
    print(f"  - {winner['golfer'].name} - Hole {winner['hole']} (Score: {winner['score']})")

# Check for duplicates in winners
golfer_names = [w['golfer'].name for w in winners]
seen = set()
duplicates = []
for name in golfer_names:
    if name in seen:
        duplicates.append(name)
    else:
        seen.add(name)

if duplicates:
    print(f"\nDUPLICATES FOUND: {duplicates}")
else:
    print("\nNo duplicates found in winners list") 