from django.shortcuts import render, redirect
from main.models import *
from main.signals import *
from main.helper import *
from main.forms import *
from django.db.models import Sum, Q
from main.season import *
from django.forms import formset_factory
from django.http import HttpResponseBadRequest, HttpResponseRedirect
from main.models import Team, Score, Sub, Week
from django.urls import reverse
from datetime import date

def get_first_half_standings(season):
    """
    Calculate first half standings (weeks 1-9) using Round models.
    Returns a list of dictionaries with team standings data.
    """
    # Get all teams for the season
    teams = Team.objects.filter(season=season)
    
    # Get all rounds for weeks 1-9 (first half)
    first_half_rounds = Round.objects.filter(
        week__season=season,
        week__number__lte=9,
        week__rained_out=False
    ).select_related('golfer', 'week', 'subbing_for')
    
    # Initialize standings dictionary
    team_standings = {}
    
    # Process each team
    for team in teams:
        team_golfers = team.golfers.all()
        team_total_points = 0
        golfer_points = {}
        
        # Calculate points for each golfer in the team
        for golfer in team_golfers:
            golfer_total = 0
            
            # 1. Rounds where golfer played for their own team (not as a sub)
            own_rounds = first_half_rounds.filter(golfer=golfer, subbing_for__isnull=True)
            own_points = own_rounds.aggregate(total=Sum('total_points'))['total'] or 0
            golfer_total += own_points
            
            # 2. Rounds where someone subbed for this golfer (points go to this golfer's team)
            sub_rounds = first_half_rounds.filter(subbing_for=golfer)
            sub_points = sub_rounds.aggregate(total=Sum('total_points'))['total'] or 0
            golfer_total += sub_points
            
            golfer_points[golfer.name] = golfer_total
            team_total_points += golfer_total
        
        # Get current handicaps for the golfers (use week 9 handicap, or latest if week 9 hasn't been played)
        golfer1 = team_golfers[0]
        golfer2 = team_golfers[1]
        
        # Try to get week 9 handicap first, fall back to latest available
        golfer1_hcp = Handicap.objects.filter(
            golfer=golfer1, 
            week__season=season,
            week__number=9
        ).first()
        
        if not golfer1_hcp:
            # If week 9 handicap doesn't exist, get the latest available
            golfer1_hcp = Handicap.objects.filter(
                golfer=golfer1, 
                week__season=season
            ).order_by('-week__number').first()
        
        golfer2_hcp = Handicap.objects.filter(
            golfer=golfer2, 
            week__season=season,
            week__number=9
        ).first()
        
        if not golfer2_hcp:
            # If week 9 handicap doesn't exist, get the latest available
            golfer2_hcp = Handicap.objects.filter(
                golfer=golfer2, 
                week__season=season
            ).order_by('-week__number').first()
        
        # Create team standings entry
        team_standings[team.id] = {
            'golfer1': golfer1.name,
            'golfer2': golfer2.name,
            'first': team_total_points,
            'golfer1FirstHcp': golfer1_hcp.handicap if golfer1_hcp else 0,
            'golfer2FirstHcp': golfer2_hcp.handicap if golfer2_hcp else 0,
        }
    
    # Convert to list and sort by total points (descending)
    standings_list = list(team_standings.values())
    standings_list.sort(key=lambda x: x['first'], reverse=True)
    
    return standings_list

def get_second_half_standings(season):
    """
    Calculate second half standings (weeks 10-18) using Round models.
    Returns a list of dictionaries with team standings data.
    """
    teams = Team.objects.filter(season=season)
    second_half_rounds = Round.objects.filter(
        week__season=season,
        week__number__gte=10,
        week__rained_out=False
    ).select_related('golfer', 'week', 'subbing_for')
    team_standings = {}
    for team in teams:
        team_golfers = team.golfers.all()
        team_total_points = 0
        for golfer in team_golfers:
            golfer_total = 0
            own_rounds = second_half_rounds.filter(golfer=golfer, subbing_for__isnull=True)
            own_points = own_rounds.aggregate(total=Sum('total_points'))['total'] or 0
            golfer_total += own_points
            sub_rounds = second_half_rounds.filter(subbing_for=golfer)
            sub_points = sub_rounds.aggregate(total=Sum('total_points'))['total'] or 0
            golfer_total += sub_points
            team_total_points += golfer_total
        golfer1 = team_golfers[0]
        golfer2 = team_golfers[1]
        golfer1_hcp = Handicap.objects.filter(golfer=golfer1, week__season=season, week__number__gte=10).order_by('-week__number').first()
        golfer2_hcp = Handicap.objects.filter(golfer=golfer2, week__season=season, week__number__gte=10).order_by('-week__number').first()
        team_standings[team.id] = {
            'golfer1': golfer1.name,
            'golfer2': golfer2.name,
            'second': team_total_points,
            'golfer1SecondHcp': golfer1_hcp.handicap if golfer1_hcp else 0,
            'golfer2SecondHcp': golfer2_hcp.handicap if golfer2_hcp else 0,
        }
    standings_list = list(team_standings.values())
    standings_list.sort(key=lambda x: x['second'], reverse=True)
    return standings_list

def get_full_standings(season):
    """
    Calculate full season standings using the sum of first and second half points for each team.
    Returns a list of dictionaries with team standings data.
    """
    teams = Team.objects.filter(season=season)
    # Get first and second half points for each team
    first_half_points = {}
    second_half_points = {}
    # First half
    first_half_rounds = Round.objects.filter(
        week__season=season,
        week__number__lte=9,
        week__rained_out=False
    ).select_related('golfer', 'week', 'subbing_for')
    # Second half
    second_half_rounds = Round.objects.filter(
        week__season=season,
        week__number__gte=10,
        week__rained_out=False
    ).select_related('golfer', 'week', 'subbing_for')
    for team in teams:
        team_golfers = team.golfers.all()
        # First half
        team_first = 0
        for golfer in team_golfers:
            own_rounds = first_half_rounds.filter(golfer=golfer, subbing_for__isnull=True)
            own_points = own_rounds.aggregate(total=Sum('total_points'))['total'] or 0
            sub_rounds = first_half_rounds.filter(subbing_for=golfer)
            sub_points = sub_rounds.aggregate(total=Sum('total_points'))['total'] or 0
            team_first += own_points + sub_points
        first_half_points[team.id] = team_first
        # Second half
        team_second = 0
        for golfer in team_golfers:
            own_rounds = second_half_rounds.filter(golfer=golfer, subbing_for__isnull=True)
            own_points = own_rounds.aggregate(total=Sum('total_points'))['total'] or 0
            sub_rounds = second_half_rounds.filter(subbing_for=golfer)
            sub_points = sub_rounds.aggregate(total=Sum('total_points'))['total'] or 0
            team_second += own_points + sub_points
        second_half_points[team.id] = team_second
    # Build standings using the sum of first and second half points
    standings = []
    for team in teams:
        team_id = team.id
        total = first_half_points[team_id] + second_half_points[team_id]
        standings.append({
            'golfer1': team.golfers.all()[0].name,
            'golfer2': team.golfers.all()[1].name,
            'total': total,
            'first': first_half_points[team_id],
            'second': second_half_points[team_id],
        })
    standings.sort(key=lambda x: x['total'], reverse=True)
    return standings

def create_season(request):
    # Set up season related information and create a new season
    if request.method == 'POST':
        form = SeasonForm(request.POST)
        if form.is_valid():
            print('Valid Form\n')
            
            # Get form data
            year = form.cleaned_data['year']
            weeks = form.cleaned_data['weeks']
            start_date = form.cleaned_data['start_date']
            
            season = Season.objects.get_or_create(year=year)[0]
            
            # Print info for debugging
            print(f'Year: {year} Type {type(year)}')
            print(f'Weeks: {weeks} Type {type(weeks)}')
            print(f'Start Date: {start_date} Type {type(start_date)}')
            create_weeks(season, weeks, start_date)

        else:
            print('Invalid Form\n')
            print(form.errors)
    
    else:
        form = SeasonForm()
    
    return render(request, 'create_season.html', {'form': form})

# Create your views here.
def main(request):
    
    # get the current years season, last week, and next week if they exist
    season = get_current_season()
    last_week = get_last_week()
    next_week = get_next_week()
    
    print(f'Season: {season}')
    print(f'Last Week: {last_week}')
    print(f'Next Week: {next_week}')
    
    # if the season exists
    if season:
        initialized = True
    else:
        initialized = False
    
    if initialized:
        
        if next_week:
            next_game = get_game(next_week)
            
            # get the weeks schedule
            next_week_schedule = get_schedule(next_week)
        else:
            next_game = None
            next_week_schedule = None
            
        if last_week:
            last_game = get_game(last_week)
            
            # check if season is in the second half
            is_second_half = last_week.number > 8
            
            # Get skins winners for last week
            skin_winners = calculate_skin_winners(last_week)
            if skin_winners:
                # Calculate skins payout (assuming $5 per person in skins)
                skins_entries = SkinEntry.objects.filter(week=last_week)
                total_skins_pot = skins_entries.count() * 5
                skin_winner_payout = total_skins_pot / len(skin_winners) if len(skin_winners) > 0 else 0
                
                # Group skin winners by golfer for template display
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
                    grouped_skin_winners[golfer_name]['total_payout'] += skin_winner_payout
            else:
                skin_winners = None
                grouped_skin_winners = None
                skin_winner_payout = 0
            
            # Get game winners for last week
            game_winners = GameEntry.objects.filter(week=last_week, winner=True).select_related('golfer', 'game')
            if game_winners.exists():
                # Calculate game payout (assuming $2 per person in each game)
                game_entries = GameEntry.objects.filter(week=last_week)
                total_game_pot = game_entries.count() * 2
                game_winner_payout = total_game_pot / game_winners.count() if game_winners.count() > 0 else 0
            else:
                game_winners = None
                game_winner_payout = 0
        else:
            last_game = None
            skin_winners = None
            grouped_skin_winners = None
            skin_winner_payout = 0
            game_winners = None
            game_winner_payout = 0
            is_second_half = False

        lastGameWinner = []


        # get standings for the current week
        #standings = getStandings(week)
        #standings = get_standings_fast(week, subs=subs, year=2022)

        # get standings in correct order
        #firstHalfStandings = sorted(standings, key=itemgetter('first'), reverse=True)
        #secondHalfStandings = sorted(standings, key=itemgetter('second'), reverse=True)
        #fullStandings = sorted(standings, key=itemgetter('total'), reverse=True)

        season_golfers = Golfer.objects.filter(team__season=season)
        
        # Calculate first half standings using Round models
        first_half_standings = get_first_half_standings(season)
        second_half_standings = []
        full_standings = []
        if is_second_half:
            second_half_standings = get_second_half_standings(season)
            full_standings = get_full_standings(season)
        
        # Pass all non-rained-out weeks ordered by date for weather bug logic
        all_weeks = Week.objects.filter(season=season, rained_out=False).order_by('date')
        
        # Find the next or current Tuesday (weekday=1) from all_weeks
        today = date.today()
        next_tuesday_date = None
        for week in all_weeks:
            week_date = week.date.date() if hasattr(week.date, 'date') else week.date
            if week_date >= today and week_date.weekday() == 1:  # 1 = Tuesday
                next_tuesday_date = week_date.strftime('%Y-%m-%d')
                break
        
        context = {
            'initialized': initialized,
            'next_week': next_week,
            'last_week': last_week,
            'next_game': next_game,
            'last_game': last_game,
            'skin_winners': skin_winners,
            'grouped_skin_winners': grouped_skin_winners,
            'skin_winner_payout': skin_winner_payout,
            'game_winners': game_winners,
            'game_winner_payout': game_winner_payout,
            'next_week_schedule': next_week_schedule,
            'firstHalfStandings': first_half_standings,
            'secondHalfStandings': second_half_standings,
            'fullStandings': full_standings,
            'is_second_half': is_second_half,
            'unestablished': [],
            'season_golfers': season_golfers,
            'all_weeks': all_weeks,
            'next_tuesday_date': next_tuesday_date,
        }
        
    else:
        
        context = {
            'initialized': initialized,
        }
        
    return render(request, 'main.html', context)

def add_scores(request):
    if request.method == 'POST':
        # Get hidden fields from the form
        week_id = request.POST.get('week_id')
        matchup_id = request.POST.get('matchup_id')

        if not week_id or not matchup_id:
            return HttpResponseBadRequest("Missing week or matchup ID.")

        try:
            week = Week.objects.get(pk=week_id)
            matchup = Matchup.objects.get(pk=matchup_id)
        except (Week.DoesNotExist, Matchup.DoesNotExist):
            return HttpResponseBadRequest("Invalid week or matchup.")

        hole_numbers = range(1, 10) if week.is_front else range(10, 19)

        # Get all active golfer rows (those that aren't grayed out)
        active_golfers = []
        for i in range(1, 11):  # Support up to 10 potential rows
            golfer_name = request.POST.get(f'golfer{i}_name')
            is_active = request.POST.get(f'golfer{i}_active') == 'true'
            
            if golfer_name and is_active:
                try:
                    golfer = Golfer.objects.get(name=golfer_name)
                    active_golfers.append((i, golfer))
                except Golfer.DoesNotExist:
                    return HttpResponseBadRequest(f"Golfer {golfer_name} not found.")

        # Process scores for each active golfer
        for row_num, golfer in active_golfers:
            for hole_number in hole_numbers:
                field_name = f'hole{hole_number}_{row_num}'
                score_value = request.POST.get(field_name)

                if not score_value:
                    return HttpResponseBadRequest(f"Missing score for {golfer.name} on hole {hole_number}.")

                try:
                    score_value = int(score_value)
                    if not (1 <= score_value <= 10):
                        return HttpResponseBadRequest(f"Score for {golfer.name} on hole {hole_number} must be between 1 and 10.")
                except ValueError:
                    return HttpResponseBadRequest(f"Score for {golfer.name} on hole {hole_number} must be a number.")

                hole = Hole.objects.get(number=hole_number, season=week.season)

                Score.objects.update_or_create(
                    golfer=golfer,
                    week=week,
                    hole=hole,
                    defaults={'score': score_value}
                )

        return redirect('add_round')

    else:
        # Load the next week + matchup info for the form
        season = Season.objects.order_by('-year').first()
        print(season.year)
        week = get_next_week()
        matchups = Matchup.objects.filter(week=week)
        front = week.is_front

        holes = Hole.objects.filter(season=season, number__in=(range(1, 10) if front else range(10, 19)))
        hole_data = [[h.par, h.handicap9, h.yards] for h in holes]
        total_yards = sum(h[2] for h in hole_data)

        return render(request, 'add_round.html', {
            'matchups': matchups,
            'hole_data': hole_data,
            'hole_numbers': [h.number for h in holes],
            'total_yards': total_yards,
            'week': week,  # needed for hidden week_id in template
        })

def add_golfer(request):
    if request.method == 'POST':
        form = GolferForm(request.POST)
        if form.is_valid():
            print('Valid Form\n')
            
            # Get form data
            name = form.cleaned_data['name']
            
            # Create the golfer object
            golfer = Golfer(
                name=name,
            )
            
            # Print info for debugging
            print(f'Name: {name}')
            
            golfer.save()
        else:
            print('Invalid Form\n')
            print(form.errors)
    else:
        form = GolferForm()
    
    return render(request, 'add_golfer.html', {'form': form})

def add_sub(request):
    current_season = Season.objects.order_by('-year').first()
    absent_golfers = Golfer.objects.filter(team__season=current_season)
    sub_golfers = Golfer.objects.all()
    weeks = Week.objects.filter(season=current_season).order_by('-date')
    
    if request.method == 'POST':
        form = SubForm(absent_golfers, sub_golfers, weeks, request.POST)
        if form.is_valid():
            print('Valid Form\n')
            print(form.cleaned_data)
            
            # Get form data
            absent_golfer_id = form.cleaned_data['absent_golfer']
            sub_golfer_id = form.cleaned_data['sub_golfer']
            week_id = form.cleaned_data['week']
            no_sub = form.cleaned_data['no_sub']
            
            # Get the golfer and week objects
            absent_golfer = Golfer.objects.get(id=absent_golfer_id)
            week = Week.objects.get(id=week_id)
            
            # Print info for debugging
            print(f'Absent Golfer: {absent_golfer.name}')
            print(f'No Sub: {no_sub}')
            print(f'Week: {week}')
            
            if sub_golfer_id == '':
                sub_golfer = None
                # Create the sub object
                sub = Sub(
                    absent_golfer=absent_golfer,
                    week=week,
                    no_sub=no_sub
                )
                print(f'Sub Golfer: None')
            else:
                sub_golfer = Golfer.objects.get(id=sub_golfer_id)
                # Create the sub object
                sub = Sub(
                    absent_golfer=absent_golfer,
                    sub_golfer=sub_golfer,
                    week=week,
                    no_sub=no_sub
                )
                print(f'Sub Golfer: {sub_golfer.name}')
            
            sub.save()
            
            # Preserve the selected week for the form reload
            # Create a new form with the same week selected
            form = SubForm(absent_golfers, sub_golfers, weeks)
            form.initial['week'] = week_id
            
        else:
            print('Invalid Form\n')
            print(form.errors.items())
    
    else:
        form = SubForm(absent_golfers, sub_golfers, weeks)
    
    return render(request, 'add_sub.html', {'form': form})

def enter_schedule(request):
    weeks = Week.objects.filter(season=Season.objects.order_by('-year').first()).order_by('-date')
    teams = Team.objects.filter(season=Season.objects.order_by('-year').first())
    
    if request.method == 'POST':
        form = ScheduleForm(weeks, teams, request.POST)
        if form.is_valid():
            print('Valid Form\n')
            
            # Get form data
            week_id = form.cleaned_data['week']
            team1_id = form.cleaned_data['team1']
            team2_id = form.cleaned_data['team2']
            
            # Get the week and team objects
            week = Week.objects.get(id=week_id)
            team1 = Team.objects.get(id=team1_id)
            team2 = Team.objects.get(id=team2_id)
            
            # Create the matchup object
            matchup = Matchup(
                week=week
            )
            matchup.save()
            
            matchup.teams.add(team1)
            matchup.teams.add(team2)
            
            # Print info for debugging
            print(f'Week: {week}')
            print(f'Team 1: {team1}')
            print(f'Team 2: {team2}')
            
            # Preserve the selected week for the form reload
            # Create a new form with the same week selected
            form = ScheduleForm(weeks, teams)
            form.initial['week'] = week_id
            
        else:
            print('Invalid Form\n')
            print(form.errors)
    else:
        form = ScheduleForm(weeks, teams)

    return render(request, 'enter_schedule.html', {'form': form})

def golfer_stats(request, golfer_id):
    import json
    from django.db.models import Avg, Count, Q, Min, Max
    
    # Get the golfer object
    golfer = Golfer.objects.get(id=golfer_id)
    
    # Get current season
    season = Season.objects.latest('year')
    
    # Get all weeks for the season
    weeks = Week.objects.filter(season=season, rained_out=False).order_by('number')
    
    # Get best and worst gross scores per year for all years the golfer has played
    yearly_gross_stats = []
    
    # Get all unique seasons where this golfer has scores
    golfer_seasons = Score.objects.filter(
        golfer=golfer
    ).values_list('week__season__year', flat=True).distinct().order_by('week__season__year')
    
    for year in golfer_seasons:
        # Get all scores for this golfer in this year
        year_scores = Score.objects.filter(
            golfer=golfer,
            week__season__year=year
        ).select_related('week', 'hole')
        
        # Group scores by week to calculate gross scores per round
        weekly_gross_scores = {}
        for score in year_scores:
            week_key = score.week.id
            if week_key not in weekly_gross_scores:
                weekly_gross_scores[week_key] = {
                    'week': score.week,
                    'scores': []
                }
            weekly_gross_scores[week_key]['scores'].append(score.score)
        
        # Calculate gross scores for each week
        gross_scores_for_year = []
        for week_data in weekly_gross_scores.values():
            if len(week_data['scores']) >= 9:  # Only count rounds with at least 9 holes
                gross_score = sum(week_data['scores'])
                gross_scores_for_year.append({
                    'week': week_data['week'],
                    'gross_score': gross_score
                })
        
        if gross_scores_for_year:
            best_gross = min(gross_scores_for_year, key=lambda x: x['gross_score'])
            worst_gross = max(gross_scores_for_year, key=lambda x: x['gross_score'])
            
            yearly_gross_stats.append({
                'year': year,
                'best_gross': best_gross,
                'worst_gross': worst_gross,
                'total_rounds': len(gross_scores_for_year),
                'avg_gross': sum(round_data['gross_score'] for round_data in gross_scores_for_year) / len(gross_scores_for_year)
            })
    
    # Calculate yearly hole-by-hole statistics
    yearly_hole_stats = {}
    hole_trends = {}
    
    for year in golfer_seasons:
        # Get all scores for this golfer in this year
        year_scores = Score.objects.filter(
            golfer=golfer,
            week__season__year=year
        ).select_related('week', 'hole')
        
        # Group scores by hole number
        hole_scores = {}
        for score in year_scores:
            hole_num = score.hole.number
            if hole_num not in hole_scores:
                hole_scores[hole_num] = []
            hole_scores[hole_num].append(score.score)
        
        # Calculate average score for each hole
        yearly_hole_stats[year] = {}
        for hole_num in range(1, 19):
            if hole_num in hole_scores and hole_scores[hole_num]:
                avg_score = sum(hole_scores[hole_num]) / len(hole_scores[hole_num])
                yearly_hole_stats[year][hole_num] = {
                    'avg_score': round(avg_score, 2),
                    'rounds_played': len(hole_scores[hole_num]),
                    'par': year_scores.filter(hole__number=hole_num).first().hole.par if year_scores.filter(hole__number=hole_num).exists() else None
                }
            else:
                yearly_hole_stats[year][hole_num] = {
                    'avg_score': None,
                    'rounds_played': 0,
                    'par': None
                }
    
    # Calculate trends (comparing to previous year)
    sorted_years = sorted(golfer_seasons)
    for i, year in enumerate(sorted_years):
        if i > 0:  # Skip first year (no previous year to compare)
            prev_year = sorted_years[i-1]
            hole_trends[year] = {}
            
            for hole_num in range(1, 19):
                current_avg = yearly_hole_stats[year][hole_num]['avg_score']
                prev_avg = yearly_hole_stats[prev_year][hole_num]['avg_score']
                
                if current_avg is not None and prev_avg is not None:
                    if current_avg < prev_avg:
                        hole_trends[year][hole_num] = 'down'  # Improved (green)
                    elif current_avg > prev_avg:
                        hole_trends[year][hole_num] = 'up'    # Worsened (red)
                    else:
                        hole_trends[year][hole_num] = 'same'  # No change
                else:
                    hole_trends[year][hole_num] = None
    
    # Get all rounds for this golfer in the season
    rounds = Round.objects.filter(
        golfer=golfer, 
        week__season=season
    ).select_related('week', 'handicap').order_by('week__number')
    
    # Get all scores for this golfer in the season for hole-by-hole analysis
    all_scores = Score.objects.filter(
        golfer=golfer,
        week__season=season
    ).select_related('hole', 'week').order_by('hole__number', 'week__number')
    
    # Get all golfer matchups for this golfer
    golfer_matchups = GolferMatchup.objects.filter(
        Q(golfer=golfer) | Q(subbing_for_golfer=golfer),
        week__season=season
    ).select_related('week', 'opponent').order_by('week__number')
    
    # Get subs information for this golfer
    subs_as_sub = Sub.objects.filter(
        sub_golfer=golfer,
        week__season=season
    ).select_related('week', 'absent_golfer').order_by('week__number')
    
    subs_for_absent = Sub.objects.filter(
        absent_golfer=golfer,
        week__season=season
    ).select_related('week', 'sub_golfer').order_by('week__number')

    # Gather points earned when someone subbed for this golfer
    subs_for_absent_with_points = []
    for sub in subs_for_absent:
        # Get the Round where someone subbed for this golfer
        round_obj = Round.objects.filter(
            week=sub.week, 
            subbing_for=golfer
        ).first()
        points = round_obj.total_points if round_obj else None
        subs_for_absent_with_points.append({
            'week': sub.week,
            'sub_golfer': sub.sub_golfer,
            'no_sub': sub.no_sub,
            'points': points,
        })

    # Gather sub points for each sub week
    subs_as_sub_with_points = []
    for sub in subs_as_sub:
        # Get the Round where this golfer subbed for the absent golfer
        round_obj = Round.objects.filter(
            week=sub.week, 
            golfer=golfer, 
            subbing_for=sub.absent_golfer
        ).first()
        points = round_obj.total_points if round_obj else None
        subs_as_sub_with_points.append({
            'week': sub.week,
            'absent_golfer': sub.absent_golfer,
            'team': [team for team in sub.absent_golfer.team_set.all() if team.season == season],
            'points': points,
        })
    
    print("subs_as_sub_with_points:", subs_as_sub_with_points)

    # Initialize data structures for charts
    handicap_data = []
    points_data = []
    gross_scores = []
    net_scores = []
    performance_vs_opponent = []
    weekly_stats = []
    
    # Process each week
    for week in weeks:
        week_round = rounds.filter(week=week).first()
        week_matchup = golfer_matchups.filter(week=week).first()
        
        if week_round and week_matchup:
            # Handicap data
            handicap_data.append({
                'week': week.number,
                'handicap': float(week_round.handicap.handicap) if week_round.handicap else 0
            })
            
            # Points data - use total points (hole points + round points)
            total_points = week_round.total_points if week_round.total_points else 0
            points_data.append({
                'week': week.number,
                'points': float(total_points)
            })
            
            # Gross and net scores
            gross_scores.append({
                'week': week.number,
                'score': week_round.gross if week_round.gross else 0
            })
            
            net_scores.append({
                'week': week.number,
                'score': week_round.net if week_round.net else 0
            })
            
            # Performance vs opponent
            opponent_round = Round.objects.filter(
                golfer=week_matchup.opponent,
                week=week
            ).first()
            
            if opponent_round:
                # Calculate net score difference (positive = golfer won, negative = opponent won)
                net_diff = (week_round.net or 0) - (opponent_round.net or 0)
                performance_vs_opponent.append({
                    'week': week.number,
                    'opponent': week_matchup.opponent.name,
                    'net_diff': net_diff,
                    'result': 'Win' if net_diff < 0 else 'Loss' if net_diff > 0 else 'Tie'
                })
            
            # Weekly stats summary
            weekly_stats.append({
                'week': week.number,
                'gross': week_round.gross or 0,
                'net': week_round.net or 0,
                'points': week_round.total_points or 0,
                'handicap': float(week_round.handicap.handicap) if week_round.handicap else 0,
                'opponent': week_matchup.opponent.name if week_matchup else 'N/A'
            })
    
    # Calculate season statistics
    if weekly_stats:
        avg_gross = sum(stat['gross'] for stat in weekly_stats) / len(weekly_stats)
        avg_net = sum(stat['net'] for stat in weekly_stats) / len(weekly_stats)
        avg_points = sum(stat['points'] for stat in weekly_stats) / len(weekly_stats)
        total_points = sum(stat['points'] for stat in weekly_stats)
        
        best_gross_week = min(weekly_stats, key=lambda x: x['gross'])
        worst_gross_week = max(weekly_stats, key=lambda x: x['gross'])
        best_net_week = min(weekly_stats, key=lambda x: x['net'])
        worst_net_week = max(weekly_stats, key=lambda x: x['net'])
        best_points_week = max(weekly_stats, key=lambda x: x['points'])
        worst_points_week = min(weekly_stats, key=lambda x: x['points'])
        
        # Performance vs opponent stats
        wins = sum(1 for perf in performance_vs_opponent if perf['result'] == 'Win')
        losses = sum(1 for perf in performance_vs_opponent if perf['result'] == 'Loss')
        ties = sum(1 for perf in performance_vs_opponent if perf['result'] == 'Tie')
        win_percentage = (wins / len(performance_vs_opponent) * 100) if performance_vs_opponent else 0
        
        # Handicap trend
        if len(handicap_data) > 1:
            handicap_trend = handicap_data[-1]['handicap'] - handicap_data[0]['handicap']
            handicap_trend_text = f"{handicap_trend:+.1f}" if handicap_trend != 0 else "No change"
            handicap_trend_positive = handicap_trend > 0
        else:
            handicap_trend_text = "N/A"
            handicap_trend_positive = False
    else:
        avg_gross = avg_net = avg_points = total_points = 0
        best_gross_week = worst_gross_week = best_net_week = worst_net_week = best_points_week = worst_points_week = None
        wins = losses = ties = win_percentage = 0
        handicap_trend_text = "N/A"
    
    # Create Plotly charts
    charts = {}
    
    if handicap_data:
        # Handicap progression chart
        handicap_chart = {
            'data': [{
                'x': [d['week'] for d in handicap_data],
                'y': [d['handicap'] for d in handicap_data],
                'type': 'scatter',
                'mode': 'lines+markers',
                'name': 'Handicap',
                'line': {'color': '#1f77b4', 'width': 3},
                'marker': {'size': 8}
            }],
            'layout': {
                'title': 'Handicap Progression',
                'xaxis': {'title': 'Week'},
                'yaxis': {'title': 'Handicap'},
                'height': 400,
                'margin': {'l': 50, 'r': 50, 't': 80, 'b': 50}
            }
        }
        charts['handicap'] = json.dumps(handicap_chart)
    
    if points_data:
        # Points per week chart
        points_chart = {
            'data': [{
                'x': [d['week'] for d in points_data],
                'y': [d['points'] for d in points_data],
                'type': 'bar',
                'name': 'Points',
                'marker': {'color': '#2ca02c'}
            }],
            'layout': {
                'title': 'Points per Week',
                'xaxis': {'title': 'Week'},
                'yaxis': {'title': 'Points'},
                'height': 400,
                'margin': {'l': 50, 'r': 50, 't': 80, 'b': 50}
            }
        }
        charts['points'] = json.dumps(points_chart)
    
    if gross_scores and net_scores:
        # Gross vs Net scores chart
        scores_chart = {
            'data': [
                {
                    'x': [d['week'] for d in gross_scores],
                    'y': [d['score'] for d in gross_scores],
                    'type': 'scatter',
                    'mode': 'lines+markers',
                    'name': 'Gross Score',
                    'line': {'color': '#ff7f0e', 'width': 3},
                    'marker': {'size': 8}
                },
                {
                    'x': [d['week'] for d in net_scores],
                    'y': [d['score'] for d in net_scores],
                    'type': 'scatter',
                    'mode': 'lines+markers',
                    'name': 'Net Score',
                    'line': {'color': '#d62728', 'width': 3},
                    'marker': {'size': 8}
                }
            ],
            'layout': {
                'title': 'Gross vs Net Scores',
                'xaxis': {'title': 'Week'},
                'yaxis': {'title': 'Score'},
                'height': 400,
                'margin': {'l': 50, 'r': 50, 't': 80, 'b': 50}
            }
        }
        charts['scores'] = json.dumps(scores_chart)
    
    if performance_vs_opponent:
        # Performance vs opponent chart
        perf_chart = {
            'data': [{
                'x': [d['week'] for d in performance_vs_opponent],
                'y': [d['net_diff'] for d in performance_vs_opponent],
                'type': 'bar',
                'name': 'Net Score Difference',
                'marker': {
                    'color': ['green' if d['net_diff'] < 0 else 'red' if d['net_diff'] > 0 else 'gray' for d in performance_vs_opponent]
                }
            }],
            'layout': {
                'title': 'Performance vs Opponent (Negative = Win)',
                'xaxis': {'title': 'Week'},
                'yaxis': {'title': 'Net Score Difference'},
                'height': 400,
                'margin': {'l': 50, 'r': 50, 't': 80, 'b': 50}
            }
        }
        charts['performance'] = json.dumps(perf_chart)
    
    # Hole-by-hole analysis
    hole_stats = {}
    scoring_breakdown = {'eagle': 0, 'birdie': 0, 'par': 0, 'bogey': 0, 'double': 0, 'triple': 0, 'worse': 0}
    all_hole_scores = []
    
    # Analyze each hole
    for hole_num in range(1, 19):
        hole_scores = all_scores.filter(hole__number=hole_num)
        if hole_scores.exists():
            scores_list = list(hole_scores.values_list('score', flat=True))
            avg_score = sum(scores_list) / len(scores_list)
            
            # Calculate scoring breakdown for this hole
            hole_par = hole_scores.first().hole.par
            for score in scores_list:
                relative_to_par = score - hole_par
                if relative_to_par <= -2:
                    scoring_breakdown['eagle'] += 1
                elif relative_to_par == -1:
                    scoring_breakdown['birdie'] += 1
                elif relative_to_par == 0:
                    scoring_breakdown['par'] += 1
                elif relative_to_par == 1:
                    scoring_breakdown['bogey'] += 1
                elif relative_to_par == 2:
                    scoring_breakdown['double'] += 1
                elif relative_to_par == 3:
                    scoring_breakdown['triple'] += 1
                else:
                    scoring_breakdown['worse'] += 1
            
            hole_stats[hole_num] = {
                'avg_score': round(avg_score, 2),
                'best_score': min(scores_list),
                'worst_score': max(scores_list),
                'rounds_played': len(scores_list),
                'par': hole_par,
                'avg_vs_par': round(avg_score - hole_par, 2),
                'scores': scores_list
            }
            all_hole_scores.append(avg_score)
        else:
            hole_stats[hole_num] = {
                'avg_score': None,
                'best_score': None,
                'worst_score': None,
                'rounds_played': 0,
                'par': None,
                'avg_vs_par': None,
                'scores': []
            }
            all_hole_scores.append(None)
    
    # Find best and worst holes (by average vs par)
    played_holes = {num: stats for num, stats in hole_stats.items() if stats['rounds_played'] > 0}
    if played_holes:
        best_hole = min(played_holes.items(), key=lambda x: x[1]['avg_vs_par'])
        worst_hole = max(played_holes.items(), key=lambda x: x[1]['avg_vs_par'])
    else:
        best_hole = worst_hole = None
    
    # Calculate consistency stats
    consistency_stats = {}
    if played_holes:
        # Standard deviation of average scores
        avg_scores = [stats['avg_score'] for stats in played_holes.values()]
        mean_avg = sum(avg_scores) / len(avg_scores)
        variance = sum((score - mean_avg) ** 2 for score in avg_scores) / len(avg_scores)
        consistency_stats['std_dev'] = round(variance ** 0.5, 2)
        
        # Range of average scores
        consistency_stats['score_range'] = round(max(avg_scores) - min(avg_scores), 2)
        
        # Holes within 0.5 strokes of average
        within_half_stroke = sum(1 for score in avg_scores if abs(score - mean_avg) <= 0.5)
        consistency_stats['holes_within_half_stroke'] = within_half_stroke
        consistency_stats['consistency_percentage'] = round((within_half_stroke / len(avg_scores)) * 100, 1)
    
    # Create hole-by-hole chart showing strokes over/under par (only for holes actually played)
    played_hole_numbers = []
    played_hole_scores = []
    played_hole_colors = []
    
    for hole_num in range(1, 19):
        if hole_stats[hole_num]['avg_vs_par'] is not None:
            played_hole_numbers.append(hole_num)
            played_hole_scores.append(hole_stats[hole_num]['avg_vs_par'])
            # Color coding: red for over par, green for under par, gray for par
            if hole_stats[hole_num]['avg_vs_par'] > 0:
                played_hole_colors.append('red')
            elif hole_stats[hole_num]['avg_vs_par'] < 0:
                played_hole_colors.append('green')
            else:
                played_hole_colors.append('gray')
    
    if played_hole_numbers:
        hole_chart = {
            'data': [{
                'x': played_hole_numbers,
                'y': played_hole_scores,
                'type': 'bar',
                'name': 'Strokes vs Par',
                'marker': {
                    'color': played_hole_colors
                }
            }],
            'layout': {
                'title': 'Average Strokes vs Par by Hole',
                'xaxis': {'title': 'Hole Number'},
                'yaxis': {'title': 'Strokes vs Par'},
                'height': 400,
                'margin': {'l': 50, 'r': 50, 't': 80, 'b': 50}
            }
        }
        charts['hole_by_hole'] = json.dumps(hole_chart)
    
    # Create yearly hole-by-hole heat map
    if yearly_hole_stats and len(yearly_hole_stats) > 1:
        # Prepare data for heat map
        years = sorted(yearly_hole_stats.keys())
        holes = list(range(1, 19))
        
        # Create z-values for heat map (strokes over/under par)
        z_values = []
        all_vs_par = []  # Collect all valid vs par values for min/max calculation
        
        for year in years:
            year_data = []
            for hole in holes:
                if yearly_hole_stats[year][hole]['avg_score'] is not None and yearly_hole_stats[year][hole]['par'] is not None:
                    avg_score = yearly_hole_stats[year][hole]['avg_score']
                    par = yearly_hole_stats[year][hole]['par']
                    vs_par = avg_score - par  # Positive = over par, negative = under par
                    year_data.append(vs_par)
                    all_vs_par.append(vs_par)
                else:
                    year_data.append(None)
            z_values.append(year_data)
        
        # Calculate min and max vs par values for better color scaling
        if all_vs_par:
            min_vs_par = min(all_vs_par)
            max_vs_par = max(all_vs_par)
            # Ensure the range is symmetric around 0 (par) for proper color scaling
            abs_max = max(abs(min_vs_par), abs(max_vs_par))
            zmin = -abs_max - 0.5  # Extend range to ensure 0 is centered
            zmax = abs_max + 0.5
        else:
            zmin = -2  # Default range: 2 under par to 2 over par
            zmax = 2
        
        # Create custom color scale that centers white at 0
        # Calculate the position of 0 in the normalized range
        zero_position = (0 - zmin) / (zmax - zmin)
        
        # Create heat map chart
        hole_heatmap = {
            'data': [{
                'z': z_values,
                'x': holes,
                'y': years,
                'type': 'heatmap',
                'colorscale': [
                    [0, 'rgb(0, 128, 0)'],      # Dark green for under par
                    [zero_position - 0.2, 'rgb(144, 238, 144)'], # Light green for near par
                    [zero_position, 'rgb(255, 255, 255)'], # White for par (0)
                    [zero_position + 0.2, 'rgb(255, 165, 0)'],  # Orange for over par
                    [1, 'rgb(255, 0, 0)']        # Red for well over par
                ],
                'zmin': zmin,
                'zmax': zmax,
                'colorbar': {
                    'title': 'Strokes vs Par',
                    'titleside': 'right',
                    'tickformat': '+.1f',
                    'tickmode': 'auto',
                    'nticks': 7
                },
                'hovertemplate': 'Year: %{y}<br>Hole: %{x}<br>Avg vs Par: %{z:+.2f}<extra></extra>'
            }],
            'layout': {
                'title': 'Yearly Hole-by-Hole Performance vs Par',
                'xaxis': {
                    'title': 'Hole Number',
                    'tickmode': 'linear',
                    'tick0': 1,
                    'dtick': 1
                },
                'yaxis': {
                    'title': 'Year',
                    'tickmode': 'linear',
                    'tick0': min(years),
                    'dtick': 1
                },
                'height': 500,
                'margin': {'l': 80, 'r': 80, 't': 80, 'b': 80}
            }
        }
        charts['yearly_hole_heatmap'] = json.dumps(hole_heatmap)
    
    # --- Opponent vs Handicap Analysis ---
    opponent_vs_hcp_list = []
    for week in weeks:
        week_round = rounds.filter(week=week).first()
        week_matchup = golfer_matchups.filter(week=week).first()
        if week_round and week_matchup:
            opponent_round = Round.objects.filter(golfer=week_matchup.opponent, week=week).first()
            if opponent_round:
                # Get par for the 9 holes played that week
                if week.is_front:
                    holes = Hole.objects.filter(season=season, number__in=range(1, 10))
                else:
                    holes = Hole.objects.filter(season=season, number__in=range(10, 19))
                week_par = sum(hole.par for hole in holes)
                opp_vs_hcp = opponent_round.net - week_par
                opponent_vs_hcp_list.append({
                    'week': week.number,
                    'opponent': week_matchup.opponent.name,
                    'opp_vs_hcp': opp_vs_hcp,
                })
            else:
                opponent_vs_hcp_list.append({
                    'week': week.number,
                    'opponent': week_matchup.opponent.name,
                    'opp_vs_hcp': None,
                })
        else:
            opponent_vs_hcp_list.append({
                'week': week.number,
                'opponent': None,
                'opp_vs_hcp': None,
            })
    # Season summary for opponent vs handicap
    opp_vs_hcp_values = [item['opp_vs_hcp'] for item in opponent_vs_hcp_list if item['opp_vs_hcp'] is not None]
    if opp_vs_hcp_values:
        avg_opp_vs_hcp = sum(opp_vs_hcp_values) / len(opp_vs_hcp_values)
        num_better = sum(1 for v in opp_vs_hcp_values if v < 0)
        num_worse = sum(1 for v in opp_vs_hcp_values if v > 0)
        num_even = sum(1 for v in opp_vs_hcp_values if v == 0)
    else:
        avg_opp_vs_hcp = 0
        num_better = num_worse = num_even = 0

    # Calculate wager statistics for this golfer
    wager_stats = {}
    
    # Calculate skins money wagered and won
    skin_entries = SkinEntry.objects.filter(golfer=golfer, week__season=season)
    total_skins_wagered = skin_entries.count() * 5  # $5 per skin entry
    
    # Calculate skins won by this golfer
    skins_won = 0
    for week in weeks:
        skin_winners = calculate_skin_winners(week)
        if skin_winners:
            # Check if this golfer won any skins this week
            week_winners = [winner for winner in skin_winners if winner['golfer'].id == golfer.id]
            if week_winners:
                # Calculate payout for this week
                week_skin_entries = SkinEntry.objects.filter(week=week)
                week_skins_pot = week_skin_entries.count() * 5
                skin_winner_payout = week_skins_pot / len(skin_winners) if len(skin_winners) > 0 else 0
                skins_won += skin_winner_payout * len(week_winners)
    
    # Calculate games money wagered and won
    game_entries = GameEntry.objects.filter(golfer=golfer, week__season=season)
    total_games_wagered = game_entries.count() * 2  # $2 per game entry
    
    # Calculate games won by this golfer
    games_won = 0
    for week in weeks:
        game_winners = GameEntry.objects.filter(week=week, golfer=golfer, winner=True)
        if game_winners.exists():
            # Calculate payout for this week
            week_game_entries = GameEntry.objects.filter(week=week)
            week_games_pot = week_game_entries.count() * 2
            total_winners = GameEntry.objects.filter(week=week, winner=True).count()
            game_winner_payout = week_games_pot / total_winners if total_winners > 0 else 0
            games_won += game_winner_payout * game_winners.count()
    
    # Calculate total earnings
    total_earned = skins_won + games_won
    total_wagered = total_skins_wagered + total_games_wagered
    net_earnings = total_earned - total_wagered
    
    wager_stats = {
        'total_skins_wagered': total_skins_wagered,
        'total_games_wagered': total_games_wagered,
        'total_wagered': total_wagered,
        'skins_won': round(skins_won, 2),
        'games_won': round(games_won, 2),
        'total_earned': round(total_earned, 2),
        'net_earnings': round(net_earnings, 2),
        'skins_entries': skin_entries.count(),
        'games_entries': game_entries.count(),
    }

    context = {
        'golfer': golfer,
        'season': season,
        'charts': charts,
        'weekly_stats': weekly_stats,
        'performance_vs_opponent': performance_vs_opponent,
        
        # Season averages
        'avg_gross': round(avg_gross, 1),
        'avg_net': round(avg_net, 1),
        'avg_points': round(avg_points, 1),
        'total_points': round(total_points, 1),
        
        # Best/Worst weeks
        'best_gross_week': best_gross_week,
        'worst_gross_week': worst_gross_week,
        'best_net_week': best_net_week,
        'worst_net_week': worst_net_week,
        'best_points_week': best_points_week,
        'worst_points_week': worst_points_week,
        
        # Match play stats
        'wins': wins,
        'losses': losses,
        'ties': ties,
        'win_percentage': round(win_percentage, 1),
        'total_matches': len(performance_vs_opponent),
        
        # Handicap trend
        'handicap_trend': handicap_trend_text,
        'handicap_trend_positive': handicap_trend_positive,
        'current_handicap': handicap_data[-1]['handicap'] if handicap_data else 'N/A',
        'starting_handicap': handicap_data[0]['handicap'] if handicap_data else 'N/A',
        
        # Subs information
        'subs_as_sub': subs_as_sub_with_points,
        'subs_for_absent': subs_for_absent_with_points,
        
        # Hole-by-hole analysis
        'hole_stats': hole_stats,
        'scoring_breakdown': scoring_breakdown,
        'best_hole': best_hole,
        'worst_hole': worst_hole,
        'consistency_stats': consistency_stats,

        # Opponent vs Handicap Analysis
        'opp_vs_hcp_list': opponent_vs_hcp_list,
        'avg_opp_vs_hcp': round(avg_opp_vs_hcp, 1),
        'num_better': num_better,
        'num_worse': num_worse,
        'num_even': num_even,
        
        # Yearly gross score statistics
        'yearly_gross_stats': yearly_gross_stats,
        
        # Yearly hole-by-hole statistics
        'yearly_hole_stats': yearly_hole_stats,
        'hole_trends': hole_trends,
        'sorted_years': sorted(yearly_hole_stats.keys()) if yearly_hole_stats else [],
        
        # Create flattened data for easier template rendering
        'yearly_hole_table_data': [
            {
                'year': year,
                'holes': [
                    {
                        'hole_num': hole_num,
                        'avg_score': yearly_hole_stats[year][hole_num]['avg_score'] if yearly_hole_stats[year][hole_num]['avg_score'] else None,
                        'par': yearly_hole_stats[year][hole_num]['par'] if yearly_hole_stats[year][hole_num]['par'] else None,
                        'vs_par': (yearly_hole_stats[year][hole_num]['avg_score'] - yearly_hole_stats[year][hole_num]['par']) if (yearly_hole_stats[year][hole_num]['avg_score'] is not None and yearly_hole_stats[year][hole_num]['par'] is not None) else None,
                        'trend': hole_trends.get(year, {}).get(hole_num) if year in hole_trends else None
                    }
                    for hole_num in range(1, 19)
                ]
            }
            for year in sorted(yearly_hole_stats.keys()) if yearly_hole_stats
        ],
        
        # Wager statistics
        'wager_stats': wager_stats,
    }
    
    return render(request, 'golfer_stats.html', context)

def sub_stats(request, golfer_id=None):
    """
    View for sub statistics - shows stats for any golfer who has subbed in the season
    """
    import json
    from django.db.models import Avg, Count, Q
    
    # Get current season
    season = Season.objects.latest('year')
    
    # Get all golfers who have subbed in the current season
    sub_golfers = Golfer.objects.filter(
        sub__week__season=season
    ).distinct().order_by('name')
    
    # Check if golfer_id is passed as query parameter (from dropdown)
    if golfer_id is None:
        golfer_id = request.GET.get('golfer_id')
    
    # If no specific golfer selected, redirect to first sub golfer or show empty state
    if golfer_id is None:
        if sub_golfers.exists():
            # Redirect to the first sub golfer
            return redirect('sub_stats_detail', golfer_id=sub_golfers.first().id)
        else:
            # No sub golfers exist, show empty state
            return render(request, 'sub_stats.html', {
                'golfer': None,
                'season': season,
                'sub_golfers': sub_golfers,
                'no_subs': True,
            })
    
    # Get the specific golfer
    try:
        golfer = Golfer.objects.get(id=golfer_id)
    except Golfer.DoesNotExist:
        if sub_golfers.exists():
            # Redirect to the first sub golfer if the requested one doesn't exist
            return redirect('sub_stats_detail', golfer_id=sub_golfers.first().id)
        else:
            return render(request, 'sub_stats.html', {
                'golfer': None,
                'season': season,
                'sub_golfers': sub_golfers,
                'no_subs': True,
            })
    
    # Get all weeks for the season
    weeks = Week.objects.filter(season=season, rained_out=False).order_by('number')
    
    # Get all rounds for this golfer in the season (only as a sub)
    rounds = Round.objects.filter(
        golfer=golfer, 
        week__season=season,
        subbing_for__isnull=False  # Only sub rounds
    ).select_related('week', 'handicap').order_by('week__number')
    
    # Get all golfer matchups for this golfer (only as a sub)
    golfer_matchups = GolferMatchup.objects.filter(
        golfer=golfer,
        week__season=season,
        subbing_for_golfer__isnull=False  # Only sub matchups
    ).select_related('week', 'opponent').order_by('week__number')
    
    # Get all scores for this golfer in the season for hole-by-hole analysis (only sub rounds)
    all_scores = Score.objects.filter(
        golfer=golfer,
        week__season=season,
        round__subbing_for__isnull=False  # Only scores from sub rounds
    ).select_related('hole', 'week').order_by('hole__number', 'week__number')
    
    # Get subs information for this golfer
    subs_as_sub = Sub.objects.filter(
        sub_golfer=golfer,
        week__season=season
    ).select_related('week', 'absent_golfer').order_by('week__number')
    
    # Gather sub points for each sub week using the new subbing_for field
    subs_as_sub_with_points = []
    for sub in subs_as_sub:
        # Get the Round where this golfer subbed for the absent golfer
        round_obj = Round.objects.filter(
            week=sub.week, 
            golfer=golfer, 
            subbing_for=sub.absent_golfer
        ).first()
        points = round_obj.total_points if round_obj else None
        subs_as_sub_with_points.append({
            'week': sub.week,
            'absent_golfer': sub.absent_golfer,
            'team': [team for team in sub.absent_golfer.team_set.all() if team.season == season],
            'points': points,
        })
    
    # Initialize data structures for charts
    handicap_data = []
    points_data = []
    gross_scores = []
    net_scores = []
    performance_vs_opponent = []
    weekly_stats = []
    
    # Process each week
    for week in weeks:
        week_round = rounds.filter(week=week).first()
        week_matchup = golfer_matchups.filter(week=week).first()
        
        if week_round and week_matchup:
            # Handicap data
            handicap_data.append({
                'week': week.number,
                'handicap': float(week_round.handicap.handicap) if week_round.handicap else 0
            })
            
            # Points data - use total points (hole points + round points)
            total_points = week_round.total_points if week_round.total_points else 0
            points_data.append({
                'week': week.number,
                'points': float(total_points)
            })
            
            # Gross and net scores
            gross_scores.append({
                'week': week.number,
                'score': week_round.gross if week_round.gross else 0
            })
            
            net_scores.append({
                'week': week.number,
                'score': week_round.net if week_round.net else 0
            })
            
            # Performance vs opponent
            opponent_round = Round.objects.filter(
                golfer=week_matchup.opponent,
                week=week
            ).first()
            
            if opponent_round:
                # Calculate net score difference (positive = golfer won, negative = opponent won)
                net_diff = (week_round.net or 0) - (opponent_round.net or 0)
                performance_vs_opponent.append({
                    'week': week.number,
                    'opponent': week_matchup.opponent.name,
                    'net_diff': net_diff,
                    'result': 'Win' if net_diff < 0 else 'Loss' if net_diff > 0 else 'Tie'
                })
            
            # Weekly stats summary
            weekly_stats.append({
                'week': week.number,
                'gross': week_round.gross or 0,
                'net': week_round.net or 0,
                'points': week_round.total_points or 0,
                'handicap': float(week_round.handicap.handicap) if week_round.handicap else 0,
                'opponent': week_matchup.opponent.name if week_matchup else 'N/A'
            })
    
    # Calculate season statistics
    if weekly_stats:
        avg_gross = sum(stat['gross'] for stat in weekly_stats) / len(weekly_stats)
        avg_net = sum(stat['net'] for stat in weekly_stats) / len(weekly_stats)
        avg_points = sum(stat['points'] for stat in weekly_stats) / len(weekly_stats)
        total_points = sum(stat['points'] for stat in weekly_stats)
        
        best_gross_week = min(weekly_stats, key=lambda x: x['gross'])
        worst_gross_week = max(weekly_stats, key=lambda x: x['gross'])
        best_net_week = min(weekly_stats, key=lambda x: x['net'])
        worst_net_week = max(weekly_stats, key=lambda x: x['net'])
        best_points_week = max(weekly_stats, key=lambda x: x['points'])
        worst_points_week = min(weekly_stats, key=lambda x: x['points'])
        
        # Performance vs opponent stats
        wins = sum(1 for perf in performance_vs_opponent if perf['result'] == 'Win')
        losses = sum(1 for perf in performance_vs_opponent if perf['result'] == 'Loss')
        ties = sum(1 for perf in performance_vs_opponent if perf['result'] == 'Tie')
        win_percentage = (wins / len(performance_vs_opponent) * 100) if performance_vs_opponent else 0
        
        # Handicap trend
        if len(handicap_data) > 1:
            handicap_trend = handicap_data[-1]['handicap'] - handicap_data[0]['handicap']
            handicap_trend_text = f"{handicap_trend:+.1f}" if handicap_trend != 0 else "No change"
            handicap_trend_positive = handicap_trend > 0
        else:
            handicap_trend_text = "N/A"
            handicap_trend_positive = False
    else:
        avg_gross = avg_net = avg_points = total_points = 0
        best_gross_week = worst_gross_week = best_net_week = worst_net_week = best_points_week = worst_points_week = None
        wins = losses = ties = win_percentage = 0
        handicap_trend_text = "N/A"
    
    # Create Plotly charts
    charts = {}
    
    if handicap_data:
        # Handicap progression chart
        handicap_chart = {
            'data': [{
                'x': [d['week'] for d in handicap_data],
                'y': [d['handicap'] for d in handicap_data],
                'type': 'scatter',
                'mode': 'lines+markers',
                'name': 'Handicap',
                'line': {'color': '#1f77b4', 'width': 3},
                'marker': {'size': 8}
            }],
            'layout': {
                'title': 'Handicap Progression',
                'xaxis': {'title': 'Week'},
                'yaxis': {'title': 'Handicap'},
                'height': 400,
                'margin': {'l': 50, 'r': 50, 't': 80, 'b': 50}
            }
        }
        charts['handicap'] = json.dumps(handicap_chart)
    
    if points_data:
        # Points per week chart
        points_chart = {
            'data': [{
                'x': [d['week'] for d in points_data],
                'y': [d['points'] for d in points_data],
                'type': 'bar',
                'name': 'Points',
                'marker': {'color': '#2ca02c'}
            }],
            'layout': {
                'title': 'Points per Week',
                'xaxis': {'title': 'Week'},
                'yaxis': {'title': 'Points'},
                'height': 400,
                'margin': {'l': 50, 'r': 50, 't': 80, 'b': 50}
            }
        }
        charts['points'] = json.dumps(points_chart)
    
    if gross_scores and net_scores:
        # Gross vs Net scores chart
        scores_chart = {
            'data': [
                {
                    'x': [d['week'] for d in gross_scores],
                    'y': [d['score'] for d in gross_scores],
                    'type': 'scatter',
                    'mode': 'lines+markers',
                    'name': 'Gross Score',
                    'line': {'color': '#ff7f0e', 'width': 3},
                    'marker': {'size': 8}
                },
                {
                    'x': [d['week'] for d in net_scores],
                    'y': [d['score'] for d in net_scores],
                    'type': 'scatter',
                    'mode': 'lines+markers',
                    'name': 'Net Score',
                    'line': {'color': '#d62728', 'width': 3},
                    'marker': {'size': 8}
                }
            ],
            'layout': {
                'title': 'Gross vs Net Scores',
                'xaxis': {'title': 'Week'},
                'yaxis': {'title': 'Score'},
                'height': 400,
                'margin': {'l': 50, 'r': 50, 't': 80, 'b': 50}
            }
        }
        charts['scores'] = json.dumps(scores_chart)
    
    if performance_vs_opponent:
        # Performance vs opponent chart
        perf_chart = {
            'data': [{
                'x': [d['week'] for d in performance_vs_opponent],
                'y': [d['net_diff'] for d in performance_vs_opponent],
                'type': 'bar',
                'name': 'Net Score Difference',
                'marker': {
                    'color': ['green' if d['net_diff'] < 0 else 'red' if d['net_diff'] > 0 else 'gray' for d in performance_vs_opponent]
                }
            }],
            'layout': {
                'title': 'Performance vs Opponent (Negative = Win)',
                'xaxis': {'title': 'Week'},
                'yaxis': {'title': 'Net Score Difference'},
                'height': 400,
                'margin': {'l': 50, 'r': 50, 't': 80, 'b': 50}
            }
        }
        charts['performance'] = json.dumps(perf_chart)
    
    # Hole-by-hole analysis
    hole_stats = {}
    scoring_breakdown = {'eagle': 0, 'birdie': 0, 'par': 0, 'bogey': 0, 'double': 0, 'triple': 0, 'worse': 0}
    all_hole_scores = []
    
    # Analyze each hole
    for hole_num in range(1, 19):
        hole_scores = all_scores.filter(hole__number=hole_num)
        if hole_scores.exists():
            scores_list = list(hole_scores.values_list('score', flat=True))
            avg_score = sum(scores_list) / len(scores_list)
            
            # Calculate scoring breakdown for this hole
            hole_par = hole_scores.first().hole.par
            for score in scores_list:
                relative_to_par = score - hole_par
                if relative_to_par <= -2:
                    scoring_breakdown['eagle'] += 1
                elif relative_to_par == -1:
                    scoring_breakdown['birdie'] += 1
                elif relative_to_par == 0:
                    scoring_breakdown['par'] += 1
                elif relative_to_par == 1:
                    scoring_breakdown['bogey'] += 1
                elif relative_to_par == 2:
                    scoring_breakdown['double'] += 1
                elif relative_to_par == 3:
                    scoring_breakdown['triple'] += 1
                else:
                    scoring_breakdown['worse'] += 1
            
            hole_stats[hole_num] = {
                'avg_score': round(avg_score, 2),
                'best_score': min(scores_list),
                'worst_score': max(scores_list),
                'rounds_played': len(scores_list),
                'par': hole_par,
                'avg_vs_par': round(avg_score - hole_par, 2),
                'scores': scores_list
            }
            all_hole_scores.append(avg_score)
        else:
            hole_stats[hole_num] = {
                'avg_score': None,
                'best_score': None,
                'worst_score': None,
                'rounds_played': 0,
                'par': None,
                'avg_vs_par': None,
                'scores': []
            }
            all_hole_scores.append(None)
    
    # Find best and worst holes (by average vs par)
    played_holes = {num: stats for num, stats in hole_stats.items() if stats['rounds_played'] > 0}
    if played_holes:
        best_hole = min(played_holes.items(), key=lambda x: x[1]['avg_vs_par'])
        worst_hole = max(played_holes.items(), key=lambda x: x[1]['avg_vs_par'])
    else:
        best_hole = worst_hole = None
    
    # Calculate consistency stats
    consistency_stats = {}
    if played_holes:
        # Standard deviation of average scores
        avg_scores = [stats['avg_score'] for stats in played_holes.values()]
        mean_avg = sum(avg_scores) / len(avg_scores)
        variance = sum((score - mean_avg) ** 2 for score in avg_scores) / len(avg_scores)
        consistency_stats['std_dev'] = round(variance ** 0.5, 2)
        
        # Range of average scores
        consistency_stats['score_range'] = round(max(avg_scores) - min(avg_scores), 2)
        
        # Holes within 0.5 strokes of average
        within_half_stroke = sum(1 for score in avg_scores if abs(score - mean_avg) <= 0.5)
        consistency_stats['holes_within_half_stroke'] = within_half_stroke
        consistency_stats['consistency_percentage'] = round((within_half_stroke / len(avg_scores)) * 100, 1)
    
    # Create hole-by-hole chart showing strokes over/under par (only for holes actually played)
    played_hole_numbers = []
    played_hole_scores = []
    played_hole_colors = []
    
    for hole_num in range(1, 19):
        if hole_stats[hole_num]['avg_vs_par'] is not None:
            played_hole_numbers.append(hole_num)
            played_hole_scores.append(hole_stats[hole_num]['avg_vs_par'])
            # Color coding: red for over par, green for under par, gray for par
            if hole_stats[hole_num]['avg_vs_par'] > 0:
                played_hole_colors.append('red')
            elif hole_stats[hole_num]['avg_vs_par'] < 0:
                played_hole_colors.append('green')
            else:
                played_hole_colors.append('gray')
    
    if played_hole_numbers:
        hole_chart = {
            'data': [{
                'x': played_hole_numbers,
                'y': played_hole_scores,
                'type': 'bar',
                'name': 'Strokes vs Par',
                'marker': {
                    'color': played_hole_colors
                }
            }],
            'layout': {
                'title': 'Average Strokes vs Par by Hole (Sub Rounds Only)',
                'xaxis': {'title': 'Hole Number'},
                'yaxis': {'title': 'Strokes vs Par'},
                'height': 400,
                'margin': {'l': 50, 'r': 50, 't': 80, 'b': 50}
            }
        }
        charts['hole_by_hole'] = json.dumps(hole_chart)
    
    context = {
        'golfer': golfer,
        'season': season,
        'charts': charts,
        'weekly_stats': weekly_stats,
        'performance_vs_opponent': performance_vs_opponent,
        'sub_golfers': sub_golfers,  # For dropdown
        
        # Season averages
        'avg_gross': round(avg_gross, 1),
        'avg_net': round(avg_net, 1),
        'avg_points': round(avg_points, 1),
        'total_points': round(total_points, 1),
        
        # Best/Worst weeks
        'best_gross_week': best_gross_week,
        'worst_gross_week': worst_gross_week,
        'best_net_week': best_net_week,
        'worst_net_week': worst_net_week,
        'best_points_week': best_points_week,
        'worst_points_week': worst_points_week,
        
        # Match play stats
        'wins': wins,
        'losses': losses,
        'ties': ties,
        'win_percentage': round(win_percentage, 1),
        'total_matches': len(performance_vs_opponent),
        
        # Handicap trend
        'handicap_trend': handicap_trend_text,
        'handicap_trend_positive': handicap_trend_positive,
        'current_handicap': handicap_data[-1]['handicap'] if handicap_data else 'N/A',
        'starting_handicap': handicap_data[0]['handicap'] if handicap_data else 'N/A',
        
        # Subs information
        'subs_as_sub': subs_as_sub_with_points,
        
        # Hole-by-hole analysis
        'hole_stats': hole_stats,
        'scoring_breakdown': scoring_breakdown,
        'best_hole': best_hole,
        'worst_hole': worst_hole,
        'consistency_stats': consistency_stats,
    }
    
    return render(request, 'sub_stats.html', context)

def scorecards(request, week):
    week_number = week
    
    week = Week.objects.get(number=week_number, season=Season.objects.latest('year'), rained_out=False)
    
    holes = list(Hole.objects.filter(
        number__in=(range(1, 10) if week.is_front else range(10, 19)),
        season=week.season
    ).order_by('number'))
    
    hole_string = "Front 9" if week.is_front else "Back 9"
    
    total_yards = sum(h.yards for h in holes)

    # Get all matchups for the week (each matchup = one scorecard)
    matchups = Matchup.objects.filter(week=week).prefetch_related('teams__golfers')
    
    if not matchups.exists():
        return render(request, 'blank_scorecards.html', {
            'error': f'No matchups found for Week {week.number}. Please enter the schedule first.'
        })
    
    # Get all golfer matchups for the week
    golfer_matchups = GolferMatchup.objects.filter(week=week).select_related(
        'golfer', 'opponent', 'subbing_for_golfer'
    )
    
    # Get all rounds for the week
    rounds = Round.objects.filter(week=week).select_related(
        'golfer', 'golfer_matchup', 'handicap'
    ).prefetch_related('scores', 'points')
    
    cards = []
    
    for matchup in matchups:
        teams = list(matchup.teams.all())
            
        team1, team2 = teams[0], teams[1]
        
        # Get all golfers from both teams
        team1_golfers = list(team1.golfers.all())
        team2_golfers = list(team2.golfers.all())
        
        # Find golfer matchups for each team's golfers
        # Check both golfer field and subbing_for_golfer field to handle subs
        team1_golfer_matchups = []
        team2_golfer_matchups = []
        
        # For team1 golfers
        for golfer in team1_golfers:
            # Find golfer matchup (could be golfer or subbing_for_golfer)
            golfer_matchup = golfer_matchups.filter(
                Q(golfer=golfer) | Q(subbing_for_golfer=golfer)
            ).first()
            
            if golfer_matchup:
                team1_golfer_matchups.append(golfer_matchup)
        
        # For team2 golfers  
        for golfer in team2_golfers:
            golfer_matchup = golfer_matchups.filter(
                Q(golfer=golfer) | Q(subbing_for_golfer=golfer)
            ).first()
            
            if golfer_matchup:
                team2_golfer_matchups.append(golfer_matchup)
        
        # Sort golfer matchups by is_A (A golfers first)
        team1_golfer_matchups.sort(key=lambda x: not x.is_A)  # True (A) comes before False (B)
        team2_golfer_matchups.sort(key=lambda x: not x.is_A)  # True (A) comes before False (B)
        
        # Create card data structure
        card = {
            'team1_golferA': None,
            'team1_golferB': None,
            'team2_golferA': None,
            'team2_golferB': None,
        }
        
        # Process team1 golfers (A and B positions)
        for i, golfer_matchup in enumerate(team1_golfer_matchups[:2]):
            golfer_data = _build_golfer_data(golfer_matchup, rounds, holes, week)
            if i == 0:
                card['team1_golferA'] = golfer_data
            else:
                card['team1_golferB'] = golfer_data
        
        # Process team2 golfers (A and B positions)
        for i, golfer_matchup in enumerate(team2_golfer_matchups[:2]):
            golfer_data = _build_golfer_data(golfer_matchup, rounds, holes, week)
            if i == 0:
                card['team2_golferA'] = golfer_data
            else:
                card['team2_golferB'] = golfer_data
        
        # Only add card if we have at least one golfer from each team
        if card['team1_golferA'] or card['team1_golferB'] or card['team2_golferA'] or card['team2_golferB']:
            cards.append(card)
    
    return render(request, 'scorecards.html', {
        "week_number": week_number,
        "holes": holes,
        "hole_string": hole_string,
        "cards": cards,
        "total": total_yards,
        "week": week,
        "hole_pars": [hole.par for hole in holes],
    })

def _build_golfer_data(golfer_matchup, rounds, holes, week):
    """Helper function to build golfer data for scorecard"""
    
    # Determine the actual golfer (could be the golfer or the sub)
    actual_golfer = golfer_matchup.golfer
    is_sub = golfer_matchup.subbing_for_golfer is not None
    sub_for = golfer_matchup.subbing_for_golfer.name if golfer_matchup.subbing_for_golfer else None
    
    # Find the round for this golfer matchup
    round_obj = rounds.filter(golfer_matchup=golfer_matchup).first()
    
    if not round_obj:
        return None
    
    # Get handicap
    hcp = round_obj.handicap.handicap if round_obj.handicap else 0
    
    # Get opponent handicap for stroke calculations
    opponent_hcp = Handicap.objects.filter(golfer=golfer_matchup.opponent, week=week).first()
    opponent_hcp_value = opponent_hcp.handicap if opponent_hcp else 0
    
    # Calculate handicap difference for strokes
    hcp_diff = conventional_round(hcp - opponent_hcp_value)  # Use conventional rounding for handicap difference
    if hcp_diff > 9:
        hcp_diff = hcp_diff - 9
        rollover = 1
    else:
        rollover = 0
    
    # Get scores for each hole
    scores = []
    hole_points = []
    stroke_info = []
    score_classes = []
    
    for hole in holes:
        # Find score for this hole
        score_obj = round_obj.scores.filter(hole=hole).first()
        score = score_obj.score if score_obj else 0
        scores.append(score)
        
        # Find points for this hole - get directly from database since Round only has current golfer's points
        points_obj = Points.objects.filter(golfer=actual_golfer, week=week, hole=hole).first()
        points = points_obj.points if points_obj else 0
        hole_points.append(points)
        

        
        # Calculate stroke info for this hole
        strokes = 0
        if hcp_diff > 0:  # Golfer is getting strokes
            if hole.handicap9 <= hcp_diff:
                strokes = 1 + rollover
            elif rollover == 1:
                strokes = 1
        stroke_info.append(strokes)
        
        # Calculate score class for color coding
        if score == 0:
            score_classes.append("")
        else:
            relative_to_par = score - hole.par
            if relative_to_par <= -2:
                score_classes.append("score-eagle")
            elif relative_to_par == -1:
                score_classes.append("score-birdie")
            elif relative_to_par == 0:
                score_classes.append("score-par")
            elif relative_to_par == 1:
                score_classes.append("score-bogey")
            elif relative_to_par == 2:
                score_classes.append("score-double")
            elif relative_to_par == 3:
                score_classes.append("score-triple")
            else:
                score_classes.append("score-worse")
    
    return {
        'golfer': actual_golfer,
        'is_sub': is_sub,
        'sub_for': sub_for,
        'hcp': hcp,
        'scores': scores,
        'hole_points': hole_points,
        'stroke_info': stroke_info,
        'score_classes': score_classes,
        'gross': round_obj.gross,
        'net': round_obj.net,
        'round_points': round_obj.round_points,
        'total_points': round_obj.total_points or 0,
    }

def set_rainout(request):
    if 'select_week' in request.POST:
        selection_form = WeekSelectionForm(request.POST)
        if selection_form.is_valid():
            
            selected_week = selection_form.cleaned_data['week']
        
            rain_out_update(selected_week)
    else:
        selection_form = WeekSelectionForm()
    
    return render(request, 'set_rainout.html', {
        'selection_form': selection_form,
    })

def create_team(request):
    
    if request.method == 'POST':
        form = TeamForm(request.POST)
        if form.is_valid():
            print('Valid Form\n')
            
            # Get form data
            golfer1 = form.cleaned_data['golfer1']
            golfer2 = form.cleaned_data['golfer2']
            season = form.cleaned_data['season']
            
            # Create the team object
            create_teams(season, [golfer1, golfer2])
            
            # Print info for debugging
            print(f'Golfer 1: {golfer1}')
            print(f'Golfer 2: {golfer2}')

        else:
            print('Invalid Form\n')
            print(form.errors)
    else:
        form = TeamForm()
    
    return render(request, 'create_team.html', {'form': form})

HoleFormSet = formset_factory(form=HoleForm, min_num=18, max_num=18, validate_min=True)

def set_holes(request):
    if request.method == 'POST':
        season_form = SeasonSelectForm(request.POST)
        formset = HoleFormSet(request.POST)
        
        if season_form.is_valid() and formset.is_valid():
            print('Valid Form\n')
            
            season = season_form.cleaned_data['year']  # Get the selected season
            
            for i, form in enumerate(formset.forms):           
                par = form.cleaned_data.get('par')
                handicap = form.cleaned_data.get('handicap')
                yards = form.cleaned_data.get('yards')
                number = i + 1
                
                if number <= 9:
                    handicap9 = (handicap + 1) // 2
                # For the second nine holes
                else:
                    handicap9 = handicap // 2
                
                # check if hole exists for the season and hole number
                hole = Hole.objects.filter(season=season, number=number)
                
                if hole.exists():
                    # Update the existing hole
                    hole = hole.first()
                    hole.par = par
                    hole.handicap = handicap
                    hole.handicap9 = handicap9
                    hole.yards = yards
                    hole.save()
                else:
                    # Create a new Hole instance
                    hole = Hole(
                        number=number,
                        par=par,
                        handicap=handicap,
                        handicap9=handicap9,
                        yards=yards,
                        season=season
                    )
                    hole.save()  # Save the instance to the database
        else:
            print('Invalid Form\n')
            # Debugging: Print errors
            if not season_form.is_valid():
                print("Season form errors:", season_form.errors)
            if not formset.is_valid():
                for form in formset:
                    print("Form errors:", form.errors)
    else:
        season_form = SeasonSelectForm()
        formset = HoleFormSet()
    return render(request, 'set_holes.html', {'season_form': season_form, 'formset': formset})

def generate_rounds_page(request):
    """View for generating rounds for a specific week"""
    from main.helper import generate_rounds, process_week, calculate_and_save_handicaps_for_season
    
    message = None
    message_type = None
    
    if request.method == 'POST':
        week_id = request.POST.get('week_id')
        recalc_all = request.POST.get('recalc_all')
        
        if recalc_all:
            # Recalculate all fully played (not rained-out, all scores entered) weeks in the current season
            try:
                current_season = Season.objects.latest('year')
                from main.helper import calculate_and_save_handicaps_for_season, generate_rounds
                calculate_and_save_handicaps_for_season(current_season)
                # Only recalculate weeks that are fully played
                played_weeks = []
                teams = Team.objects.filter(season=current_season)
                for week in Week.objects.filter(season=current_season, rained_out=False).order_by('number'):
                    no_sub_golfer_count = Sub.objects.filter(week=week, no_sub=True).count()
                    expected_scores = ((teams.count() * 2) - no_sub_golfer_count) * 9
                    actual_scores = Score.objects.filter(week=week).count()
                    if actual_scores == expected_scores:
                        played_weeks.append(week)
                # Only recalc played weeks
                for week in played_weeks:
                    from main.helper import process_week
                    process_week(week)
                message = f"Successfully recalculated all played weeks for {current_season.year}."
                message_type = "success"
            except Exception as e:
                message = f"Error recalculating all played weeks: {str(e)}"
                message_type = "error"
        elif week_id:
            try:
                week = Week.objects.get(id=week_id)
                
                # First, ensure handicaps are calculated for the season
                calculate_and_save_handicaps_for_season(week.season)

                generate_golfer_matchups(week)
                
                # Generate rounds for the week
                golfer_matchups = GolferMatchup.objects.filter(week=week)
                
                if golfer_matchups.exists():
                    # Process each golfer matchup to generate rounds
                    for golfer_matchup in golfer_matchups:
                        generate_round(golfer_matchup)
                    
                    message = f"Successfully generated handicaps and rounds for Week {week.number} ({week.date.date()})"
                    message_type = "success"
                else:
                    message = f"No golfer matchups found for Week {week.number}. Please ensure the schedule has been entered."
                    message_type = "warning"
                    
            except Week.DoesNotExist:
                message = "Selected week not found."
                message_type = "error"
            except Exception as e:
                message = f"Error generating rounds: {str(e)}"
                message_type = "error"
        else:
            message = "Please select a week."
            message_type = "error"
    
    # Get all weeks from the current season
    current_season = Season.objects.latest('year')
    weeks = Week.objects.filter(season=current_season, rained_out=False).order_by('number')
    
    context = {
        'weeks': weeks,
        'message': message,
        'message_type': message_type,
    }
    
    return render(request, 'generate_rounds.html', context)

def league_stats(request):
    """
    View for league-wide statistics and leaderboards
    """
    import json
    from django.db.models import Avg, Count, Min, Max, Q
    
    # Get current season
    season = Season.objects.latest('year')
    
    # Get all weeks for the season
    weeks = Week.objects.filter(season=season, rained_out=False).order_by('number')
    
    # Get all rounds for the season (excluding subs)
    rounds = Round.objects.filter(
        week__season=season,
        subbing_for__isnull=True  # Exclude sub rounds
    ).select_related('golfer', 'week', 'handicap').order_by('week__number')
    
    # Get all scores for hole-by-hole analysis (excluding subs)
    all_scores = Score.objects.filter(
        week__season=season,
        round__subbing_for__isnull=True  # Exclude scores from sub rounds
    ).select_related('hole', 'week', 'golfer').order_by('hole__number', 'week__number')
    
    # League Averages
    league_stats = {}
    
    # Overall averages
    if rounds.exists():
        league_stats['avg_gross'] = rounds.aggregate(avg=Avg('gross'))['avg']
        league_stats['avg_net'] = rounds.aggregate(avg=Avg('net'))['avg']
        league_stats['avg_points'] = rounds.aggregate(avg=Avg('total_points'))['avg']
        league_stats['avg_handicap'] = rounds.aggregate(avg=Avg('handicap__handicap'))['avg']
        
        # Best and worst scores
        best_gross = rounds.order_by('gross').first()
        worst_gross = rounds.order_by('-gross').first()
        best_net = rounds.order_by('net').first()
        worst_net = rounds.order_by('-net').first()
        best_points = rounds.order_by('-total_points').first()
        worst_points = rounds.order_by('total_points').first()
        
        league_stats['best_gross'] = {
            'score': best_gross.gross,
            'golfer': best_gross.golfer.name,
            'week': best_gross.week.number
        }
        league_stats['worst_gross'] = {
            'score': worst_gross.gross,
            'golfer': worst_gross.golfer.name,
            'week': worst_gross.week.number
        }
        league_stats['best_net'] = {
            'score': best_net.net,
            'golfer': best_net.golfer.name,
            'week': best_net.week.number
        }
        league_stats['worst_net'] = {
            'score': worst_net.net,
            'golfer': worst_net.golfer.name,
            'week': worst_net.week.number
        }
        league_stats['best_points'] = {
            'score': best_points.total_points,
            'golfer': best_points.golfer.name,
            'week': best_points.week.number
        }
        league_stats['worst_points'] = {
            'score': worst_points.total_points,
            'golfer': worst_points.golfer.name,
            'week': worst_points.week.number
        }
    
    # Weekly Leaders
    weekly_leaders = []
    for week in weeks:
        week_rounds = rounds.filter(week=week)
        if week_rounds.exists():
            best_gross_week = week_rounds.order_by('gross').first()
            worst_gross_week = week_rounds.order_by('-gross').first()
            best_net_week = week_rounds.order_by('net').first()
            worst_net_week = week_rounds.order_by('-net').first()
            best_points_week = week_rounds.order_by('-total_points').first()
            
            weekly_leaders.append({
                'week': week.number,
                'date': week.date.strftime('%m/%d'),
                'is_front': week.is_front,
                'best_gross': {
                    'score': best_gross_week.gross,
                    'golfer': best_gross_week.golfer.name
                },
                'worst_gross': {
                    'score': worst_gross_week.gross,
                    'golfer': worst_gross_week.golfer.name
                },
                'best_net': {
                    'score': best_net_week.net,
                    'golfer': best_net_week.golfer.name
                },
                'worst_net': {
                    'score': worst_net_week.net,
                    'golfer': worst_net_week.golfer.name
                },
                'best_points': {
                    'score': best_points_week.total_points,
                    'golfer': best_points_week.golfer.name
                }
            })
    
    # Hole-by-hole league averages
    hole_stats = {}
    for hole_num in range(1, 19):
        hole_scores = all_scores.filter(hole__number=hole_num)
        if hole_scores.exists():
            avg_score = hole_scores.aggregate(avg=Avg('score'))['avg']
            best_score = hole_scores.aggregate(min=Min('score'))['min']
            worst_score = hole_scores.aggregate(max=Max('score'))['max']
            total_rounds = hole_scores.count()
            
            # Get par for this hole
            hole_par = hole_scores.first().hole.par
            
            hole_stats[hole_num] = {
                'avg_score': round(avg_score, 2),
                'best_score': best_score,
                'worst_score': worst_score,
                'total_rounds': total_rounds,
                'par': hole_par,
                'avg_vs_par': round(avg_score - hole_par, 2)
            }
    
    # Scoring breakdown (eagles, birdies, pars, etc.)
    scoring_breakdown = {'eagle': 0, 'birdie': 0, 'par': 0, 'bogey': 0, 'double': 0, 'triple': 0, 'worse': 0}
    total_holes = 0
    
    for hole_num in range(1, 19):
        hole_scores = all_scores.filter(hole__number=hole_num)
        if hole_scores.exists():
            hole_par = hole_scores.first().hole.par
            for score_obj in hole_scores:
                score = score_obj.score
                relative_to_par = score - hole_par
                if relative_to_par <= -2:
                    scoring_breakdown['eagle'] += 1
                elif relative_to_par == -1:
                    scoring_breakdown['birdie'] += 1
                elif relative_to_par == 0:
                    scoring_breakdown['par'] += 1
                elif relative_to_par == 1:
                    scoring_breakdown['bogey'] += 1
                elif relative_to_par == 2:
                    scoring_breakdown['double'] += 1
                elif relative_to_par == 3:
                    scoring_breakdown['triple'] += 1
                else:
                    scoring_breakdown['worse'] += 1
                total_holes += 1
    
    # Calculate percentages
    scoring_percentages = {}
    for score_type, count in scoring_breakdown.items():
        if total_holes > 0:
            scoring_percentages[score_type] = round((count / total_holes) * 100, 1)
        else:
            scoring_percentages[score_type] = 0
    
    # Golfer performance rankings
    golfer_stats = {}
    for round_obj in rounds:
        golfer_name = round_obj.golfer.name
        if golfer_name not in golfer_stats:
            golfer_stats[golfer_name] = {
                'rounds_played': 0,
                'total_gross': 0,
                'total_net': 0,
                'total_points': 0,
                'best_gross': float('inf'),
                'worst_gross': 0,
                'best_net': float('inf'),
                'worst_net': 0,
                'best_points': 0,
                'worst_points': float('inf')
            }
        
        stats = golfer_stats[golfer_name]
        stats['rounds_played'] += 1
        stats['total_gross'] += round_obj.gross
        stats['total_net'] += round_obj.net
        stats['total_points'] += round_obj.total_points or 0
        
        if round_obj.gross < stats['best_gross']:
            stats['best_gross'] = round_obj.gross
        if round_obj.gross > stats['worst_gross']:
            stats['worst_gross'] = round_obj.gross
            
        if round_obj.net < stats['best_net']:
            stats['best_net'] = round_obj.net
        if round_obj.net > stats['worst_net']:
            stats['worst_net'] = round_obj.net
            
        if (round_obj.total_points or 0) > stats['best_points']:
            stats['best_points'] = round_obj.total_points or 0
        if (round_obj.total_points or 0) < stats['worst_points']:
            stats['worst_points'] = round_obj.total_points or 0
    
    # Calculate averages and create rankings
    golfer_rankings = []
    for golfer_name, stats in golfer_stats.items():
        if stats['rounds_played'] > 0:
            avg_gross = stats['total_gross'] / stats['rounds_played']
            avg_net = stats['total_net'] / stats['rounds_played']
            avg_points = stats['total_points'] / stats['rounds_played']
            
            golfer_rankings.append({
                'name': golfer_name,
                'rounds_played': stats['rounds_played'],
                'avg_gross': round(avg_gross, 1),
                'avg_net': round(avg_net, 1),
                'avg_points': round(avg_points, 1),
                'best_gross': stats['best_gross'],
                'worst_gross': stats['worst_gross'],
                'best_net': stats['best_net'],
                'worst_net': stats['worst_net'],
                'best_points': stats['best_points'],
                'worst_points': stats['worst_points'],
                'total_points': stats['total_points']
            })
    
    # Sort rankings
    gross_rankings = sorted(golfer_rankings, key=lambda x: x['avg_gross'])
    net_rankings = sorted(golfer_rankings, key=lambda x: x['avg_net'])
    points_rankings = sorted(golfer_rankings, key=lambda x: x['avg_points'], reverse=True)
    
    # Add rankings to each golfer
    for i, golfer in enumerate(gross_rankings):
        golfer['gross_rank'] = i + 1
    for i, golfer in enumerate(net_rankings):
        golfer['net_rank'] = i + 1
    for i, golfer in enumerate(points_rankings):
        golfer['points_rank'] = i + 1
    
    # Most consistent golfer (lowest standard deviation of net scores)
    consistency_rankings = []
    for golfer_name, stats in golfer_stats.items():
        if stats['rounds_played'] > 1:
            # Get all net scores for this golfer
            golfer_rounds = rounds.filter(golfer__name=golfer_name)
            net_scores = list(golfer_rounds.values_list('net', flat=True))
            
            # Calculate standard deviation
            mean_net = sum(net_scores) / len(net_scores)
            variance = sum((score - mean_net) ** 2 for score in net_scores) / len(net_scores)
            std_dev = variance ** 0.5
            
            consistency_rankings.append({
                'name': golfer_name,
                'std_dev': round(std_dev, 2),
                'rounds_played': stats['rounds_played']
            })
    
    consistency_rankings.sort(key=lambda x: x['std_dev'])
    for i, golfer in enumerate(consistency_rankings):
        golfer['rank'] = i + 1
    
    # Money/Earnings Analysis
    money_stats = {}
    
    # Calculate skins money
    skin_entries = SkinEntry.objects.filter(week__season=season)
    total_skins_wagered = skin_entries.count() * 5  # $5 per skin entry
    
    # Calculate skins won by golfer
    golfer_skins_won = {}
    for week in weeks:
        skin_winners = calculate_skin_winners(week)
        if skin_winners:
            # Calculate payout for this week
            week_skin_entries = SkinEntry.objects.filter(week=week)
            week_skins_pot = week_skin_entries.count() * 5
            skin_winner_payout = week_skins_pot / len(skin_winners) if len(skin_winners) > 0 else 0
            
            # Group by golfer
            for winner in skin_winners:
                golfer_name = winner['golfer'].name
                if golfer_name not in golfer_skins_won:
                    golfer_skins_won[golfer_name] = 0
                golfer_skins_won[golfer_name] += skin_winner_payout
    
    # Calculate games money
    game_entries = GameEntry.objects.filter(week__season=season)
    total_games_wagered = game_entries.count() * 2  # $2 per game entry
    
    # Calculate games won by golfer
    golfer_games_won = {}
    for week in weeks:
        game_winners = GameEntry.objects.filter(week=week, winner=True).select_related('golfer', 'game')
        if game_winners.exists():
            # Calculate payout for this week
            week_game_entries = GameEntry.objects.filter(week=week)
            week_games_pot = week_game_entries.count() * 2
            game_winner_payout = week_games_pot / game_winners.count() if game_winners.count() > 0 else 0
            
            # Group by golfer
            for winner in game_winners:
                golfer_name = winner.golfer.name
                if golfer_name not in golfer_games_won:
                    golfer_games_won[golfer_name] = 0
                golfer_games_won[golfer_name] += game_winner_payout
    
    # Calculate total earnings by golfer
    golfer_total_earnings = {}
    all_golfers = set(list(golfer_skins_won.keys()) + list(golfer_games_won.keys()))
    
    for golfer_name in all_golfers:
        skins_earned = golfer_skins_won.get(golfer_name, 0)
        games_earned = golfer_games_won.get(golfer_name, 0)
        total_earned = skins_earned + games_earned
        
        golfer_total_earnings[golfer_name] = {
            'skins_earned': round(skins_earned, 2),
            'games_earned': round(games_earned, 2),
            'total_earned': round(total_earned, 2)
        }
    
    # Create top 5 leaderboard
    earnings_leaderboard = sorted(
        golfer_total_earnings.items(), 
        key=lambda x: x[1]['total_earned'], 
        reverse=True
    )[:5]
    
    # Find golfer with most skins money
    most_skins_golfer = max(golfer_skins_won.items(), key=lambda x: x[1]) if golfer_skins_won else None
    
    # Find golfer with most games money
    most_games_golfer = max(golfer_games_won.items(), key=lambda x: x[1]) if golfer_games_won else None
    
    money_stats = {
        'total_skins_wagered': total_skins_wagered,
        'total_games_wagered': total_games_wagered,
        'total_wagered': total_skins_wagered + total_games_wagered,
        'most_skins_golfer': {
            'name': most_skins_golfer[0],
            'amount': round(most_skins_golfer[1], 2)
        } if most_skins_golfer else None,
        'most_games_golfer': {
            'name': most_games_golfer[0],
            'amount': round(most_games_golfer[1], 2)
        } if most_games_golfer else None,
        'earnings_leaderboard': earnings_leaderboard
    }
    
    # Create charts
    charts = {}
    
    # Hole-by-hole league average chart
    if hole_stats:
        hole_numbers = list(hole_stats.keys())
        avg_scores = [hole_stats[num]['avg_score'] for num in hole_numbers]
        avg_vs_par = [hole_stats[num]['avg_vs_par'] for num in hole_numbers]
        
        hole_chart = {
            'data': [{
                'x': hole_numbers,
                'y': avg_vs_par,
                'type': 'bar',
                'name': 'League Avg vs Par',
                'marker': {
                    'color': ['red' if score > 0 else 'green' if score < 0 else 'gray' for score in avg_vs_par]
                }
            }],
            'layout': {
                'title': 'League Average vs Par by Hole',
                'xaxis': {'title': 'Hole Number'},
                'yaxis': {'title': 'Strokes vs Par'},
                'height': 400,
                'margin': {'l': 50, 'r': 50, 't': 80, 'b': 50}
            }
        }
        charts['hole_by_hole'] = json.dumps(hole_chart)
    
    # Scoring breakdown pie chart
    if scoring_breakdown:
        score_types = list(scoring_breakdown.keys())
        counts = list(scoring_breakdown.values())
        colors = ['#FFD700', '#FFA500', '#32CD32', '#FF6347', '#8B0000', '#4B0082', '#000000']
        
        pie_chart = {
            'data': [{
                'labels': score_types,
                'values': counts,
                'type': 'pie',
                'marker': {'colors': colors[:len(score_types)]}
            }],
            'layout': {
                'title': 'League Scoring Breakdown',
                'height': 400,
                'margin': {'l': 50, 'r': 50, 't': 80, 'b': 50}
            }
        }
        charts['scoring_breakdown'] = json.dumps(pie_chart)
    
    context = {
        'season': season,
        'league_stats': league_stats,
        'weekly_leaders': weekly_leaders,
        'hole_stats': hole_stats,
        'scoring_breakdown': scoring_breakdown,
        'scoring_percentages': scoring_percentages,
        'gross_rankings': gross_rankings[:10],  # Top 10
        'net_rankings': net_rankings[:10],      # Top 10
        'points_rankings': points_rankings[:10], # Top 10
        'consistency_rankings': consistency_rankings[:10], # Top 10
        'charts': charts,
        'total_rounds': rounds.count(),
        'total_golfers': len(golfer_stats),
        'total_holes': total_holes,
        'money_stats': money_stats,
    }
    
    return render(request, 'league_stats.html', context)

def calculate_skin_winners(week):
    """
    Automatically calculate skin winners based on gross scores.
    A skin is won when a golfer has the best gross score on a hole alone.
    """
    # Get all golfers in skins for this week
    skin_entries = SkinEntry.objects.filter(week=week)
    if not skin_entries.exists():
        return []
    
    # Get the holes for this week (front 9 or back 9)
    if week.is_front:
        holes = Hole.objects.filter(season=week.season, number__in=range(1, 10))
    else:
        holes = Hole.objects.filter(season=week.season, number__in=range(10, 19))
    
    # Dictionary to group skins by golfer
    golfer_skins = {}
    
    # Check each hole for skin winners
    for hole in holes:
        # Get all scores for this hole from golfers in skins
        scores = []
        for skin_entry in skin_entries:
            score_obj = Score.objects.filter(
                golfer=skin_entry.golfer,
                week=week,
                hole=hole
            ).first()
            if score_obj:
                scores.append((skin_entry.golfer, score_obj.score))
        
        if scores:
            # Find the best score
            best_score = min(scores, key=lambda x: x[1])[1]
            
            # Count how many golfers have the best score
            best_score_golfers = [golfer for golfer, score in scores if score == best_score]
            
            # If only one golfer has the best score, they win the skin
            if len(best_score_golfers) == 1:
                winner = best_score_golfers[0]
                if winner not in golfer_skins:
                    golfer_skins[winner] = []
                golfer_skins[winner].append({
                    'hole': hole.number,
                    'score': best_score
                })
    
    # Convert to list format for template compatibility
    skin_winners = []
    for golfer, skins in golfer_skins.items():
        for skin in skins:
            skin_winners.append({
                'golfer': golfer,
                'hole': skin['hole'],
                'score': skin['score']
            })
    
    return skin_winners

def manage_skins(request):
    """View for managing skins entries and automatically calculating winners"""
    message = None
    message_type = None
    selected_week = None
    current_season = Season.objects.order_by('-year').first()
    if request.method == 'POST':
        if 'add_skins_entry' in request.POST:
            form = SkinEntryForm(request.POST)
            if form.is_valid():
                week = form.cleaned_data['week']
                golfers = form.cleaned_data['golfers']
                selected_week = week  # Preserve selected week
                # Clear existing entries for this week
                SkinEntry.objects.filter(week=week).delete()
                # Create new entries
                for golfer in golfers:
                    SkinEntry.objects.create(
                        golfer=golfer,
                        week=week
                    )
                message = f"Successfully added {len(golfers)} golfers to skins for Week {week.number}"
                message_type = "success"
            else:
                message = "Please correct the errors below."
                message_type = "error"
                # Preserve selected week even on error
                if 'week' in form.cleaned_data:
                    selected_week = form.cleaned_data['week']
    else:
        # Set default week in form initial for GET
        default_week = get_next_week()
        initial = {}
        if default_week:
            initial['week'] = default_week.id
        form = SkinEntryForm(initial=initial)
        selected_week = default_week  # Ensure JS loads golfers for default week
    # Get skins entries for current season
    skins_entries = {}
    if current_season:
        weeks = Week.objects.filter(season=current_season).order_by('-number')
        for week in weeks:
            entries = SkinEntry.objects.filter(week=week).select_related('golfer')
            if entries.exists():
                # Calculate skin winners for display
                skin_winners = calculate_skin_winners(week)
                # Calculate individual payouts
                total_pot = entries.count() * 5
                if skin_winners:
                    # Each skin is worth total pot divided by number of skins
                    per_skin_value = total_pot / len(skin_winners)
                    # Count how many skins each golfer won
                    golfer_skin_counts = {}
                    for winner in skin_winners:
                        golfer_name = winner['golfer'].name
                        if golfer_name not in golfer_skin_counts:
                            golfer_skin_counts[golfer_name] = 0
                        golfer_skin_counts[golfer_name] += 1
                    # Calculate individual payouts (per skin value × number of skins won)
                    for winner in skin_winners:
                        winner['payout'] = per_skin_value
                        winner['total_payout'] = golfer_skin_counts[winner['golfer'].name] * per_skin_value
                else:
                    per_skin_value = 0
                skins_entries[week] = {
                    'entries': entries,
                    'winners': skin_winners,
                    'total_pot': total_pot,
                    'per_skin_value': per_skin_value
                }
    context = {
        'form': form,
        'skins_entries': skins_entries,
        'message': message,
        'message_type': message_type,
        'selected_week': selected_week,
    }
    return render(request, 'manage_skins.html', context)

def manage_games(request):
    """View for managing game entries and winners"""
    message = None
    message_type = None
    selected_week = None
    selected_game = None
    current_season = Season.objects.order_by('-year').first()
    if request.method == 'POST':
        if 'create_game' in request.POST:
            form = CreateGameForm(request.POST)
            if form.is_valid():
                name = form.cleaned_data['name']
                desc = form.cleaned_data['desc']
                week = form.cleaned_data['week']
                Game.objects.create(name=name, desc=desc, week=week)
                return HttpResponseRedirect(f"{reverse('manage_games')}?week={week.id}")
            else:
                message = "Please correct the errors below."
                message_type = "error"
                selected_week = form.cleaned_data.get('week')
        elif 'add_game_entry' in request.POST:
            form = GameEntryForm(request.POST)
            if form.is_valid():
                week = form.cleaned_data['week']
                golfers = form.cleaned_data['golfers']
                selected_week = week  # Preserve selected week
                game = Game.objects.filter(week=week).first()
                if not game:
                    message = f"No game has been created for Week {week.number}. Please create a game first."
                    message_type = "error"
                else:
                    GameEntry.objects.filter(week=week, game=game).delete()
                    for golfer in golfers:
                        GameEntry.objects.create(
                            golfer=golfer,
                            week=week,
                            game=game
                        )
                    return HttpResponseRedirect(f"{reverse('manage_games')}?week={week.id}")
            else:
                message = "Please correct the errors below."
                message_type = "error"
                selected_week = form.cleaned_data.get('week')
        elif 'add_game_winner' in request.POST:
            form = GameWinnerForm(request.POST)
            if form.is_valid():
                week = form.cleaned_data['week']
                winner = form.cleaned_data['winner']
                game = Game.objects.filter(week=week).first()
                if not game:
                    message = f"No game has been created for Week {week.number}. Please create a game first."
                    message_type = "error"
                else:
                    if GameEntry.objects.filter(golfer=winner, week=week, game=game).exists():
                        GameEntry.objects.filter(week=week, game=game, winner=True).update(winner=False)
                        game_entry = GameEntry.objects.get(golfer=winner, week=week, game=game)
                        game_entry.winner = True
                        game_entry.save()
                        return HttpResponseRedirect(f"{reverse('manage_games')}?week={week.id}")
                    else:
                        message = f"{winner.name} is not in {game.name} for Week {week.number}"
                        message_type = "error"
            else:
                message = "Please correct the errors below."
                message_type = "error"
                selected_week = form.cleaned_data.get('week')
        # Always re-initialize forms with selected_week for persistence
        form = GameEntryForm(initial_week=selected_week)
        winner_form = GameWinnerForm(initial_week=selected_week)
        create_form = CreateGameForm()
    else:
        # GET: check for ?week= param
        week_id = request.GET.get('week')
        selected_week = None
        if week_id:
            try:
                selected_week = Week.objects.get(pk=week_id)
            except Exception:
                selected_week = None
        if not selected_week:
            # Set default week in form data for GET
            default_week = get_next_week()
            if default_week:
                selected_week = default_week
        form_data = {}
        if selected_week:
            form_data['week'] = selected_week.id
        form = GameEntryForm(data=form_data, initial_week=selected_week)
        winner_form = GameWinnerForm(initial_week=selected_week)
        create_form = CreateGameForm()
    # Get game entries for current season
    game_entries = {}
    if current_season:
        weeks = Week.objects.filter(season=current_season).order_by('-number')
        for week in weeks:
            entries = GameEntry.objects.filter(week=week).select_related('golfer', 'game')
            if entries.exists():
                # Calculate payouts for each game
                game_data = {}
                for entry in entries:
                    game = entry.game
                    if game not in game_data:
                        game_data[game] = {
                            'entries': [],
                            'winners': [],
                            'total_pot': 0,
                            'winner_payout': 0
                        }
                    game_data[game]['entries'].append(entry)
                    game_data[game]['total_pot'] += 2  # $2 per entry
                    if entry.winner:
                        game_data[game]['winners'].append(entry)
                # Calculate winner payouts
                for game, data in game_data.items():
                    if data['winners']:
                        data['winner_payout'] = data['total_pot'] / len(data['winners'])
                game_entries[week] = game_data
    # Get all games
    games = Game.objects.all().order_by('name')
    context = {
        'form': form,
        'winner_form': winner_form,
        'create_form': create_form,
        'game_entries': game_entries,
        'games': games,
        'message': message,
        'message_type': message_type,
        'selected_week': selected_week,
        'selected_game': selected_game,
    }
    return render(request, 'manage_games.html', context)

def blank_scorecards(request):
    """View for blank scorecards for the next week to be played"""
    
    # Get the next week
    week = get_next_week()
    
    if not week:
        return render(request, 'blank_scorecards.html', {
            'error': 'No next week found. The season may be complete or not started.'
        })
    
    holes = list(Hole.objects.filter(
        number__in=(range(1, 10) if week.is_front else range(10, 19)),
        season=week.season
    ).order_by('number'))
    
    hole_string = "Front 9" if week.is_front else "Back 9"
    total_yards = sum(h.yards for h in holes)

    # Get all matchups for the week (each matchup = one scorecard)
    matchups = Matchup.objects.filter(week=week).prefetch_related('teams__golfers')
    
    # Get all golfer matchups for the week
    golfer_matchups = GolferMatchup.objects.filter(week=week).select_related(
        'golfer', 'opponent', 'subbing_for_golfer'
    )
    
    if not golfer_matchups.exists():
        return render(request, 'blank_scorecards.html', {
            'error': f'No golfer matchups found for Week {week.number}. Please generate rounds first.'
        })
    
    cards = []
    
    for matchup in matchups:
        teams = list(matchup.teams.all())
            
        team1, team2 = teams[0], teams[1]
        
        # Get all golfers from both teams
        team1_golfers = list(team1.golfers.all())
        team2_golfers = list(team2.golfers.all())
        
        # Find golfer matchups for each team's golfers
        team1_golfer_matchups = []
        team2_golfer_matchups = []
        
        # For team1 golfers
        for golfer in team1_golfers:
            golfer_matchup = golfer_matchups.filter(
                Q(golfer=golfer) | Q(subbing_for_golfer=golfer)
            ).first()
            
            if golfer_matchup:
                team1_golfer_matchups.append(golfer_matchup)
        
        # For team2 golfers  
        for golfer in team2_golfers:
            golfer_matchup = golfer_matchups.filter(
                Q(golfer=golfer) | Q(subbing_for_golfer=golfer)
            ).first()
            
            if golfer_matchup:
                team2_golfer_matchups.append(golfer_matchup)
        
        # Sort golfer matchups by is_A (A golfers first)
        team1_golfer_matchups.sort(key=lambda x: not x.is_A)
        team2_golfer_matchups.sort(key=lambda x: not x.is_A)
        
        # Create card data structure
        card = {
            'team1_golferA': None,
            'team1_golferB': None,
            'team2_golferA': None,
            'team2_golferB': None,
        }
        
        # Process team1 golfers (A and B positions)
        for i, golfer_matchup in enumerate(team1_golfer_matchups[:2]):
            golfer_data = _build_blank_golfer_data(golfer_matchup, holes, week)
            if i == 0:
                card['team1_golferA'] = golfer_data
            else:
                card['team1_golferB'] = golfer_data
        
        # Process team2 golfers (A and B positions)
        for i, golfer_matchup in enumerate(team2_golfer_matchups[:2]):
            golfer_data = _build_blank_golfer_data(golfer_matchup, holes, week)
            if i == 0:
                card['team2_golferA'] = golfer_data
            else:
                card['team2_golferB'] = golfer_data
        
        # Only add card if we have at least one golfer from each team
        if card['team1_golferA'] or card['team1_golferB'] or card['team2_golferA'] or card['team2_golferB']:
            cards.append(card)
    
    # Define senior tee holes (holes where seniors can play up)
    senior_tee_holes = {1, 2, 4, 6, 9, 10, 12, 14, 17}
    
    return render(request, 'blank_scorecards.html', {
        "week_number": week.number,
        "holes": holes,
        "hole_string": hole_string,
        "cards": cards,
        "total": total_yards,
        "week": week,
        "hole_pars": [hole.par for hole in holes],
        "senior_tee_holes": senior_tee_holes,
    })

def _build_blank_golfer_data(golfer_matchup, holes, week):
    """Helper function to build blank golfer data for scorecard"""
    
    # Determine the actual golfer (could be the golfer or the sub)
    actual_golfer = golfer_matchup.golfer
    is_sub = golfer_matchup.subbing_for_golfer is not None
    sub_for = golfer_matchup.subbing_for_golfer.name if golfer_matchup.subbing_for_golfer else None
    
    # Get handicap
    hcp_obj = Handicap.objects.filter(golfer=actual_golfer, week=week).first()
    hcp = hcp_obj.handicap if hcp_obj else 0
    
    # Get opponent handicap for stroke calculations
    opponent_hcp = golfer_matchup.opponent.handicap_set.filter(week=week).first()
    opponent_hcp_value = opponent_hcp.handicap if opponent_hcp else 0
    
    # Calculate handicap difference for strokes
    hcp_diff = conventional_round(hcp) - conventional_round(opponent_hcp_value)
    if hcp_diff > 9:
        hcp_diff = hcp_diff - 9
        rollover = 1
    else:
        rollover = 0
    
    # Calculate stroke info for each hole (for visual indication)
    stroke_info = []
    
    for hole in holes:
        strokes = 0
        if hcp_diff > 0:  # Golfer is getting strokes
            if hole.handicap9 <= hcp_diff:
                strokes = 1 + rollover
            elif rollover == 1:
                strokes = 1
        stroke_info.append(strokes)
    
    return {
        'golfer': actual_golfer,
        'is_sub': is_sub,
        'sub_for': sub_for,
        'hcp': hcp,
        'stroke_info': stroke_info,
        'scores': ['' for _ in holes],  # Empty scores
        'hole_points': ['' for _ in holes],  # Empty points
        'gross': '',
        'net': '',
        'round_points': '',
        'total_points': '',
    }