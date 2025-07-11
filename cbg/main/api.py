from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.db.models import Q
from main.models import GolferMatchup, Matchup, Sub
from main.serializers import GolferSerializer
from main.helper import get_absent_team_from_sub

def get_matchup_data(request, matchup_id):
    matchup = get_object_or_404(Matchup, pk=matchup_id)
    week = matchup.week

    # Get golfer matchups for this week and matchup
    golfer_matchups = GolferMatchup.objects.filter(
        week=week).filter(
            Q(golfer__in=matchup.teams.all().values_list('golfers', flat=True)) |
            Q(subbing_for_golfer__in=matchup.teams.all().values_list('golfers', flat=True))
    )

    # Build dynamic rows based on actual playing golfers
    rows = []
    row_counter = 1
    
    # First, collect all playing golfers with their data
    playing_golfers = []
    
    for golfer_matchup in golfer_matchups:
        # Check if this golfer is actually playing (not absent with no sub)
        is_playing = True
        playing_for = None
        
        if golfer_matchup.subbing_for_golfer:
            sub = Sub.objects.filter(week=week, absent_golfer=golfer_matchup.subbing_for_golfer).first()
            if sub and sub.no_sub:
                is_playing = False
            else:
                playing_for = golfer_matchup.subbing_for_golfer.name
        
        if is_playing:
            handicap = getattr(golfer_matchup.golfer.handicap_set.filter(week=week).first(), 'handicap', 0)
            
            playing_golfers.append({
                'golfer_matchup': golfer_matchup,
                'golfer_name': golfer_matchup.golfer.name,
                'handicap': handicap,
                'playing_for': playing_for,
                'golfer_id': golfer_matchup.golfer.id,
                'is_A': golfer_matchup.is_A,
                'team': get_absent_team_from_sub(golfer_matchup.golfer, week) if playing_for is not None else golfer_matchup.golfer.team_set.get(season=week.season),
                'opponent': golfer_matchup.opponent
            })
    
    # Sort golfers by handicap (lower handicaps first = better golfers on top) and then by not is_A (A players first)
    playing_golfers.sort(key=lambda x: (x['handicap'], not x['is_A']))
    
    # Group golfers into pairings (2 golfers per pairing)
    pairings = []
    for i in range(0, len(playing_golfers), 2):
        pairing = playing_golfers[i:i+2]
        pairings.append(pairing)
    
    # Now build the rows from the sorted pairings
    for pairing_index, pairing in enumerate(pairings):
        for i, golfer in enumerate(pairing):
            rows.append({
                'row_num': row_counter,
                'golfer_name': golfer['golfer_name'],
                'handicap': golfer['handicap'],
                'is_editable': True,
                'playing_for': golfer['playing_for'],
                'golfer_id': golfer['golfer_id'],
                'pairing_index': pairing_index,
                'is_pairing_start': i == 0  # Start of pairing if first golfer in pairing
            })
            row_counter += 1

    return JsonResponse({'rows': rows})
