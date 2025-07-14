#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cbg.settings')
django.setup()

from main.models import *
from main.views import calculate_skin_winners

def test_skin_grouping():
    """
    Test the skin winner grouping logic
    """
    print("Testing skin winner grouping...")
    
    # Get current season
    current_season = Season.objects.order_by('-year').first()
    if not current_season:
        print("No season found")
        return
    
    print(f"Testing with season: {current_season.year}")
    
    # Get all weeks with skin entries
    weeks_with_skins = Week.objects.filter(
        season=current_season,
        skinentry__isnull=False
    ).distinct().order_by('-number')
    
    print(f"Found {weeks_with_skins.count()} weeks with skin entries")
    
    for week in weeks_with_skins[:5]:  # Test first 5 weeks
        print(f"\n--- Week {week.number} ---")
        
        # Calculate skin winners
        skin_winners = calculate_skin_winners(week)
        print(f"Found {len(skin_winners)} total skin wins")
        
        if skin_winners:
            # Group skin winners by golfer
            grouped_skin_winners = {}
            for winner in skin_winners:
                golfer_name = winner['golfer'].name
                if golfer_name not in grouped_skin_winners:
                    grouped_skin_winners[golfer_name] = {
                        'golfer': winner['golfer'],
                        'skins': [],
                        'total_payout': 0
                    }
                grouped_skin_winners[golfer_name]['skins'].append({
                    'hole': winner['hole'],
                    'score': winner['score']
                })
                # Assuming $5 per skin entry, calculate payout
                skins_entries = SkinEntry.objects.filter(week=week)
                total_skins_pot = skins_entries.count() * 5
                skin_winner_payout = total_skins_pot / len(skin_winners) if len(skin_winners) > 0 else 0
                grouped_skin_winners[golfer_name]['total_payout'] += skin_winner_payout
            
            print(f"Grouped by {len(grouped_skin_winners)} golfers:")
            for golfer_name, golfer_data in grouped_skin_winners.items():
                skin_details = []
                for skin in golfer_data['skins']:
                    skin_details.append(f"Hole {skin['hole']} ({skin['score']})")
                print(f"  {golfer_name}: {', '.join(skin_details)} - ${golfer_data['total_payout']:.2f}")
        else:
            print("No skin winners found")
            
        # Check if there are scores for this week
        scores_count = Score.objects.filter(week=week).count()
        print(f"Scores in database: {scores_count}")

if __name__ == "__main__":
    test_skin_grouping() 