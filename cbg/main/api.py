from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.db.models import Q
from main.models import GolferMatchup, Matchup, Sub, Week, Team, Game, GameEntry, SkinEntry
from main.helper import get_absent_team_from_sub

def get_playing_golfers(request, week_id):
    """API endpoint to get all golfers playing in a specific week"""
    week = get_object_or_404(Week, pk=week_id)
    
    # Get all teams for the season
    teams = Team.objects.filter(season=week.season)
    playing_golfers = []
    
    # Get existing skin entries for this week
    existing_skin_entries = set(SkinEntry.objects.filter(week=week).values_list('golfer_id', flat=True))
    
    for team in teams:
        team_golfers = team.golfers.all()
        for golfer in team_golfers:
            # Check if golfer is playing (not absent or has a sub)
            sub = Sub.objects.filter(week=week, absent_golfer=golfer).first()
            if not sub or (sub and sub.sub_golfer):
                # Golfer is playing (either directly or via sub)
                if sub and sub.sub_golfer:
                    playing_golfers.append({
                        'id': sub.sub_golfer.id,
                        'name': sub.sub_golfer.name,
                        'is_sub': True,
                        'subbing_for': golfer.name,
                        'in_skins': sub.sub_golfer.id in existing_skin_entries
                    })
                else:
                    playing_golfers.append({
                        'id': golfer.id,
                        'name': golfer.name,
                        'is_sub': False,
                        'subbing_for': None,
                        'in_skins': golfer.id in existing_skin_entries
                    })
    
    # Sort by name
    playing_golfers.sort(key=lambda x: x['name'])
    
    return JsonResponse({'golfers': playing_golfers})


def get_games_for_week(request, week_id):
    """API endpoint to get all games for a specific week"""
    week = get_object_or_404(Week, pk=week_id)
    
    # Get games that have entries for this week
    games = Game.objects.filter(gameentry__week=week).distinct().order_by('name')
    
    games_data = []
    for game in games:
        games_data.append({
            'id': game.id,
            'name': game.name,
            'desc': game.desc
        })
    
    return JsonResponse({'games': games_data})


def get_games_by_week(request, week_id):
    """API endpoint to get games for a specific week (for game creation)"""
    week = get_object_or_404(Week, pk=week_id)
    games = Game.objects.filter(week=week).order_by('name')
    
    games_data = []
    for game in games:
        games_data.append({
            'id': game.id,
            'name': game.name,
            'desc': game.desc or ''
        })
    
    return JsonResponse({'games': games_data})


def get_game_entries(request, week_id, game_id):
    """API endpoint to get all entries for a specific game in a specific week"""
    week = get_object_or_404(Week, pk=week_id)
    game = get_object_or_404(Game, pk=game_id)
    
    entries = GameEntry.objects.filter(week=week, game=game).select_related('golfer')
    
    entries_data = []
    for entry in entries:
        entries_data.append({
            'golfer_id': entry.golfer.id,
            'golfer_name': entry.golfer.name,
            'winner': entry.winner
        })
    
    return JsonResponse({'entries': entries_data})


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
    
    # Sort golfers by is_A status first (A golfers on top) and then by handicap (lower handicaps first)
    playing_golfers.sort(key=lambda x: (not x['is_A'], x['handicap']))
    
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


def get_week_matchups(request):
    week_id = request.GET.get('week_id')
    if not week_id:
        return JsonResponse({'error': 'No week_id provided'}, status=400)
    try:
        week = Week.objects.get(id=week_id)
    except Week.DoesNotExist:
        return JsonResponse({'error': 'Week not found'}, status=404)
    matchups = Matchup.objects.filter(week=week).prefetch_related('teams__golfers')
    team_ids = list(matchups.values_list('teams__id', flat=True))
    # Build current matchup pairings as list of dicts with golfer names
    matchup_pairs = []
    for matchup in matchups:
        teams = list(matchup.teams.all())
        if len(teams) == 2:
            team1_golfers = [g.name for g in teams[0].golfers.all()]
            team2_golfers = [g.name for g in teams[1].golfers.all()]
            matchup_pairs.append({
                'team1': team1_golfers,
                'team2': team2_golfers
            })
        elif len(teams) == 1:
            team1_golfers = [g.name for g in teams[0].golfers.all()]
            matchup_pairs.append({
                'team1': team1_golfers,
                'team2': []
            })
    return JsonResponse({'team_ids': team_ids, 'matchup_pairs': matchup_pairs})