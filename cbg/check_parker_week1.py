#!/usr/bin/env python
import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'cbg.settings')
django.setup()

from main.models import *
from main.helper import *
from django.db.models import Sum
import math

def conventional_round(value):
    """Conventional rounding: 0.5 and up round up, under 0.5 round down."""
    return math.floor(value + 0.5)

def check_parker_week1():
    print("=== Checking Parker's Week 1 Data ===\n")
    
    # Get Parker and Week 1
    try:
        parker = Golfer.objects.get(name__icontains='Parker')
        week1 = Week.objects.get(number=1, season=Season.objects.latest('year'))
        print(f"Found golfer: {parker.name}")
        print(f"Found week: Week {week1.number} ({week1.date.date()})")
        print(f"Front/Back: {'Front' if week1.is_front else 'Back'}")
        print()
        
        # Get Parker's handicap for week 1
        parker_hcp = Handicap.objects.get(golfer=parker, week=week1)
        print(f"Parker's handicap: {parker_hcp.handicap}")
        print(f"Parker's rounded handicap: {conventional_round(parker_hcp.handicap)}")
        print()
        
        # Get Parker's matchup and opponent
        golfer_matchup = GolferMatchup.objects.get(golfer=parker, week=week1)
        opponent = golfer_matchup.opponent
        print(f"Parker's opponent: {opponent.name}")
        
        # Get opponent's handicap
        opponent_hcp = Handicap.objects.get(golfer=opponent, week=week1)
        print(f"Opponent's handicap: {opponent_hcp.handicap}")
        print(f"Opponent's rounded handicap: {conventional_round(opponent_hcp.handicap)}")
        print()
        
        # Calculate handicap difference
        hcp_diff_raw = parker_hcp.handicap - opponent_hcp.handicap
        hcp_diff_rounded = conventional_round(hcp_diff_raw)
        print(f"Handicap difference (raw): {hcp_diff_raw}")
        print(f"Handicap difference (rounded): {hcp_diff_rounded}")
        
        # Determine who gets strokes
        if hcp_diff_rounded > 0:
            print(f"Parker gets {hcp_diff_rounded} strokes")
            getting_strokes = True
            giving_strokes = False
        elif hcp_diff_rounded < 0:
            print(f"Parker gives {abs(hcp_diff_rounded)} strokes")
            getting_strokes = False
            giving_strokes = True
        else:
            print("No strokes given")
            getting_strokes = False
            giving_strokes = False
        
        # Calculate rollover
        if abs(hcp_diff_rounded) > 9:
            rollover = 1
            adjusted_diff = abs(hcp_diff_rounded) - 9
            print(f"Rollover: {rollover}, Adjusted difference: {adjusted_diff}")
        else:
            rollover = 0
            adjusted_diff = abs(hcp_diff_rounded)
            print(f"Rollover: {rollover}, Adjusted difference: {adjusted_diff}")
        print()
        
        # Get holes for the week
        if week1.is_front:
            holes = Hole.objects.filter(season=week1.season, number__range=(1, 9)).order_by('number')
        else:
            holes = Hole.objects.filter(season=week1.season, number__range=(10, 18)).order_by('number')
        
        # Get scores
        parker_scores = Score.objects.filter(golfer=parker, week=week1)
        opponent_scores = Score.objects.filter(golfer=opponent, week=week1)
        
        print("=== Hole-by-Hole Analysis ===")
        print("Hole | Par | Hcp9 | Parker | Opp | Parker+Strokes | Opp+Strokes | Points")
        print("-----|-----|------|--------|-----|----------------|-------------|-------")
        
        total_points = 0
        
        for hole in holes:
            parker_score_obj = parker_scores.get(hole=hole)
            opponent_score_obj = opponent_scores.get(hole=hole)
            
            parker_gross = parker_score_obj.score
            opponent_gross = opponent_score_obj.score
            
            # Calculate strokes for this hole
            strokes = 0
            if adjusted_diff > 0:
                if hole.handicap9 <= adjusted_diff:
                    strokes = 1 + rollover
                elif rollover == 1:
                    strokes = 1
            
            # Apply strokes
            if getting_strokes:
                parker_net = parker_gross - strokes
                opponent_net = opponent_gross
            elif giving_strokes:
                parker_net = parker_gross
                opponent_net = opponent_gross - strokes
            else:
                parker_net = parker_gross
                opponent_net = opponent_gross
            
            # Calculate points
            if parker_net < opponent_net:
                points = 1
                result = "W"
            elif parker_net == opponent_net:
                points = 0.5
                result = "T"
            else:
                points = 0
                result = "L"
            
            total_points += points
            
            print(f"{hole.number:4} | {hole.par:3} | {hole.handicap9:4} | {parker_gross:6} | {opponent_gross:3} | {parker_net:14} | {opponent_net:11} | {points:5} ({result})")
        
        print(f"\nTotal hole points: {total_points}")
        
        # Calculate round points
        parker_gross_total = parker_scores.aggregate(Sum('score'))['score__sum']
        opponent_gross_total = opponent_scores.aggregate(Sum('score'))['score__sum']
        
        parker_net_total = parker_gross_total - conventional_round(parker_hcp.handicap)
        opponent_net_total = opponent_gross_total - conventional_round(opponent_hcp.handicap)
        
        print(f"\nParker gross total: {parker_gross_total}")
        print(f"Opponent gross total: {opponent_gross_total}")
        print(f"Parker net total: {parker_net_total}")
        print(f"Opponent net total: {opponent_net_total}")
        
        if parker_net_total < opponent_net_total:
            round_points = 3
            print(f"Round points: {round_points} (Parker wins round)")
        elif parker_net_total == opponent_net_total:
            round_points = 1.5
            print(f"Round points: {round_points} (Tie)")
        else:
            round_points = 0
            print(f"Round points: {round_points} (Opponent wins round)")
        
        total_points += round_points
        print(f"Total points: {total_points}")
        
        # Check what's stored in the database
        try:
            round_obj = Round.objects.get(golfer=parker, week=week1)
            print(f"\nDatabase values:")
            print(f"Round total_points: {round_obj.total_points}")
            print(f"Round round_points: {round_obj.round_points}")
            
            # Check individual hole points
            print(f"\nIndividual hole points from database:")
            for hole in holes:
                points_obj = Points.objects.filter(golfer=parker, week=week1, hole=hole).first()
                if points_obj:
                    print(f"Hole {hole.number}: {points_obj.points}")
        except Round.DoesNotExist:
            print("No Round object found for Parker in week 1")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_parker_week1() 