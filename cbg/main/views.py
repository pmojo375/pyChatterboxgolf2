from django.shortcuts import render, redirect
from main.models import *
from main.signals import *
from main.helper import *
from main.forms import *
from django.db.models import Sum
from datetime import datetime
import json
from main.season import *
from django.forms import formset_factory

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
            
            if last_game:
                game_winners = get_game_winners(last_game)
                if game_winners:
                    game_winner_payout = (GameEntry.objects.filter(week=last_week).count() * 2) / len(game_winners)
                else:
                    game_winner_payout = 0
            else:
                game_winners = None
                game_winner_payout = 0
        else:
            last_game = None
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
        
        context = {
            'initialized': initialized,
            'next_week': next_week,
            'last_week': last_week,
            'next_game': next_game,
            'last_game': last_game,
            'game_winners': game_winners,
            'game_winner_payout': game_winner_payout,
            'next_week_schedule': next_week_schedule,
            'firstHalfStandings': [],
            'secondHalfStandings': [],
            'fullStandings': [],
            'is_second_half': is_second_half,
            'unestablished': [],
            'season_golfers': season_golfers,
        }
        
    else:
    
        context = {
            'initialized': initialized,
        }
        
    return render(request, 'main.html', context)

def add_scores(request):
    if request.method == 'POST':
        
        form = RoundForm(request.POST)
        if form.is_valid():
            print('Valid Form\n')

            # Get form data
            matchup = int(form.cleaned_data['matchup'])

            # create the golfer matchups
            team1_golferA = Golfer.objects.get(id=form.golfer_data[matchup][0][1])
            team2_golferA = Golfer.objects.get(id=form.golfer_data[matchup][1][1])
            team1_golferB = Golfer.objects.get(id=form.golfer_data[matchup][2][1])
            team2_golferB = Golfer.objects.get(id=form.golfer_data[matchup][3][1])
            
            golfers = []
            
            # add golfers to list and check if they are already in the list
            if team1_golferA not in golfers:
                golfers.append(team1_golferA)
            if team2_golferA not in golfers:
                golfers.append(team2_golferA)
            if team1_golferB not in golfers:
                golfers.append(team1_golferB)
            if team2_golferB not in golfers:
                golfers.append(team2_golferB)

            week = Week.objects.get(number=3, season=Season.objects.order_by('-year').first())
            front = week.is_front

            holes = Hole.objects.filter(season=week.season)

            # Create the score objects
            for golfer_num in range(1, 5):
                golfer = Golfer.objects.get(id=form.golfer_data[matchup][golfer_num-1][1])
                for hole in range(1, 10):
                    field_name = f'hole{hole}_{golfer_num}'
                    score = int(form.cleaned_data[field_name])

                    # update hole number if playing back 9
                    if not front:
                        hole = hole + 9
                        
                    hole = holes.get(number=hole)
                    print(f'{golfer} - Hole {hole.number} - {score}')
                    #Score.objects.update_or_create(golfer=golfer, week=week, hole=hole, score=score)

            # Create the golfer matchup objects
            
            print(f'{team1_golferA} vs {team2_golferA}')
            print(f'{team1_golferB} vs {team2_golferB}')
            
            matchup1, _ = GolferMatchup.objects.update_or_create(week=week, golfer=team1_golferA, opponent=team2_golferA, is_A=True)
            matchup2, _ = GolferMatchup.objects.update_or_create(week=week, golfer=team1_golferB, opponent=team2_golferB, is_A=False)
            matchup3, _ = GolferMatchup.objects.update_or_create(week=week, golfer=team2_golferA, opponent=team1_golferA, is_A=True)
            matchup4, _ = GolferMatchup.objects.update_or_create(week=week, golfer=team2_golferB, opponent=team1_golferB, is_A=False)

            matchups = [matchup1, matchup2, matchup3, matchup4]

            if Week.objects.filter(season=week.season, number=week.number+1).exists():
                next_week = Week.objects.get(season=week.season, number=week.number+1)

            # generate handicaps for the next week
            for golfer in golfers:
                calculate_handicap(golfer, week.season, next_week)

            # calculate points for the week
            for matchup in matchups:
                generate_round(matchup)
        else:
            print('Invalid Form\n')
            print(form.errors)
            
    else:
        form = RoundForm()
    
    golfer_data_json = json.dumps(form.golfer_data)
    hole_data_raw = Hole.objects.filter(season=Season.objects.order_by('-year').first())

    hole_data = []

    # determine if playing front or back
    season = Season.objects.order_by('-year').first()
    week = Week.objects.get(season=season, number=3, rained_out=False)
    front = week.is_front

    if front:
        hole_numbers = range(1, 10)
    else:
        hole_numbers = range(10, 19)

    for hole in hole_data_raw:
        if front:
            if hole.number < 10:
                hole_data.append([hole.par, hole.handicap9, hole.yards])
        else:
            if hole.number > 9:
                hole_data.append([hole.par, hole.handicap9, hole.yards])
    
    # get total yard for the holes
    total_yards = 0
    for hole in hole_data:
        total_yards += hole[2]

    return render(request, 'add_round.html', {'form': form, 'golfer_data_json': golfer_data_json, 'hole_data': hole_data, 'hole_numbers': hole_numbers, 'total_yards': total_yards})

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
            
            # Get form data
            absent_golfer_id = form.cleaned_data['absent_golfer']
            sub_golfer_id = form.cleaned_data['sub_golfer']
            week_id = form.cleaned_data['week']
            
            # Get the golfer and week objects
            absent_golfer = Golfer.objects.get(id=absent_golfer_id)
            sub_golfer = Golfer.objects.get(id=sub_golfer_id)
            week = Week.objects.get(id=week_id)
            
            # Create the sub object
            sub = Sub(
                absent_golfer=absent_golfer,
                sub_golfer=sub_golfer,
                week=week
            )
            
            # Print info for debugging
            print(f'Absent Golfer: {absent_golfer.name}')
            print(f'Sub Golfer: {sub_golfer.name}')
            print(f'Week: {week}')
            
            sub.save()
        else:
            print('Invalid Form\n')
            print(form.errors)
    
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
            
        else:
            print('Invalid Form\n')
            print(form.errors)
    else:
        form = ScheduleForm(weeks, teams)

    return render(request, 'enter_schedule.html', {'form': form})

def golfer_stats(request, golfer_id):
    
    # Get the golfer object
    golfer = Golfer.objects.get(id=golfer_id)
    
    # Get season
    season = Season.objects.latest('year')

    # Get the best gross week
    
    score_sums = Score.objects.filter(golfer=golfer, week__season=season).values('week__number').annotate(total_score=Sum('score')).order_by('total_score')
    
    best_gross_week = score_sums.first()
    worst_gross_week = score_sums.last()
    
    print(best_gross_week)
    print(worst_gross_week)
    
    context = {
        'golfer_name': golfer.name,
        'best_gross_week': best_gross_week['week__number'],
        'worst_gross_week': worst_gross_week['week__number'],
        'best_gross_score': best_gross_week['total_score'],
        'worst_gross_score': worst_gross_week['total_score'],
    }

    
    return render(request, 'golfer_stats.html', context)

def scorecards(request, week):
    # Retrieve necessary data from the models
    week_number = week
    week = Week.objects.get(number=week, season=Season.objects.latest('year'), rained_out=False)
    teams = Team.objects.all()
    hole_data = Hole.objects.all()
    matchups = Matchup.objects.filter(week=week)
    
    if week.is_front:
        holes_nums = range(1,10)
        hole_string = 'Front 9'
    else:
        holes_nums = range(10,19)
        hole_string = 'Back 9'
        
    holes = Hole.objects.filter(number__in=holes_nums, season=week.season)
    
    cards = []
    
    for matchup in matchups:
        teams = matchup.teams.all()
        team1 = teams[0]
        team2 = teams[1]
        
        team1_golfers = team1.golfers.all()
        team2_golfers = team2.golfers.all()
        
        team1_golfer1 = team1_golfers[0]
        team1_golfer2 = team1_golfers[1]
        team2_golfer1 = team2_golfers[0]
        team2_golfer2 = team2_golfers[1]
        
        team1_golfer1 = get_sub(team1_golfer1, week)
        team1_golfer2 = get_sub(team1_golfer2, week)
        team2_golfer1 = get_sub(team2_golfer1, week)
        team2_golfer2 = get_sub(team2_golfer2, week)
        
        team1_golfer1_hcp = get_hcp(team1_golfer1, week)
        team1_golfer2_hcp = get_hcp(team1_golfer2, week)
        team2_golfer1_hcp = get_hcp(team2_golfer1, week)
        team2_golfer2_hcp = get_hcp(team2_golfer2, week)
        
        # team 1 golfer 1 has a higher handicap than team 1 golfer 2, designate the A and B golfers
        if team1_golfer1_hcp >= team1_golfer2_hcp:
            team1_golferA = team1_golfer2
            team1_golferB = team1_golfer1
            team1_golferA_hcp = team1_golfer2_hcp
            team1_golferB_hcp = team1_golfer1_hcp
        else:
            team1_golferA = team1_golfer1
            team1_golferB = team1_golfer2
            team1_golferA_hcp = team1_golfer1_hcp
            team1_golferB_hcp = team1_golfer2_hcp
            
        # team 2 golfer 1 has a higher handicap than team 2 golfer 2, designate the A and B golfers
        if team2_golfer1_hcp >= team2_golfer2_hcp:
            team2_golferA = team2_golfer2
            team2_golferB = team2_golfer1
            team2_golferA_hcp = team2_golfer2_hcp
            team2_golferB_hcp = team2_golfer1_hcp
        else:
            team2_golferA = team2_golfer1
            team2_golferB = team2_golfer2
            team2_golferA_hcp = team2_golfer1_hcp
            team2_golferB_hcp = team2_golfer2_hcp
            
        team1_golferA_scores_query = Score.objects.filter(golfer=team1_golferA, week=week).order_by('hole__number')
        team1_golferB_scores_query = Score.objects.filter(golfer=team1_golferB, week=week).order_by('hole__number')
        team2_golferA_scores_query = Score.objects.filter(golfer=team2_golferA, week=week).order_by('hole__number')
        team2_golferB_scores_query = Score.objects.filter(golfer=team2_golferB, week=week).order_by('hole__number')
        
        team1_golferA_scores = []
        team1_golferB_scores = []
        team2_golferA_scores = []
        team2_golferB_scores = []
        
        team1_golferA_css = []
        team1_golferB_css = []
        team2_golferA_css = []
        team2_golferB_css = []
        
        matchupA_point_data = get_golfer_points(week, team1_golferA, detail=True)
        matchupB_point_data = get_golfer_points(week, team1_golferB, detail=True)
        
        team1_golferA_hole_points = matchupA_point_data['hole_data']
        team2_golferA_hole_points = matchupA_point_data['opponents_hole_data']
        team1_golferB_hole_points = matchupB_point_data['hole_data']
        team2_golferB_hole_points = matchupB_point_data['opponents_hole_data']
        
        for index, score in enumerate(team1_golferA_scores_query):
            team1_golferA_scores.append(score.score)
            team1_golferA_css.append(get_score_string(team1_golferA_hole_points[index], holes))
        for index, score in enumerate(team1_golferB_scores_query):
            team1_golferB_scores.append(score.score)
            team1_golferB_css.append(get_score_string(team1_golferB_hole_points[index], holes))
        for index, score in enumerate(team2_golferA_scores_query):
            team2_golferA_scores.append(score.score)
            team2_golferA_css.append(get_score_string(team2_golferA_hole_points[index], holes))
        for index, score in enumerate(team2_golferB_scores_query):
            team2_golferB_scores.append(score.score)
            team2_golferB_css.append(get_score_string(team2_golferB_hole_points[index], holes))
            
        team1_golferA_total = sum(team1_golferA_scores)
        team1_golferB_total = sum(team1_golferB_scores)
        team2_golferA_total = sum(team2_golferA_scores)
        team2_golferB_total = sum(team2_golferB_scores)
        
        team1_golferA_net = team1_golferA_total - team1_golferA_hcp
        team1_golferB_net = team1_golferB_total - team1_golferB_hcp
        team2_golferA_net = team2_golferA_total - team2_golferA_hcp
        team2_golferB_net = team2_golferB_total - team2_golferB_hcp
        
        
        team1_golferA_round_points = matchupA_point_data['round_points']
        team2_golferA_round_points = matchupA_point_data['opponents_round_points']
        team1_golferB_round_points = matchupB_point_data['round_points']
        team2_golferB_round_points = matchupB_point_data['opponents_round_points']
        
        team1_golferA_total_points = matchupA_point_data['golfer_points']
        team2_golferA_total_points = matchupA_point_data['opponent_points']
        team1_golferB_total_points = matchupB_point_data['golfer_points']
        team2_golferB_total_points = matchupB_point_data['opponent_points']
        
        cards.append({
        'team1_golferA': team1_golferA,
        'team1_golferB': team1_golferB,
        'team2_golferA': team2_golferA,
        'team2_golferB': team2_golferB,
        'team1_golferA_hcp': team1_golferA_hcp,
        'team1_golferB_hcp': team1_golferB_hcp,
        'team2_golferA_hcp': team2_golferA_hcp,
        'team2_golferB_hcp': team2_golferB_hcp,
        'team1_golferA_total': team1_golferA_total,
        'team1_golferB_total': team1_golferB_total,
        'team2_golferA_total': team2_golferA_total,
        'team2_golferB_total': team2_golferB_total,
        'team1_golferA_net': team1_golferA_net,
        'team1_golferB_net': team1_golferB_net,
        'team2_golferA_net': team2_golferA_net,
        'team2_golferB_net': team2_golferB_net,
        'team1_golferA_scores': zip(team1_golferA_scores, team1_golferA_css),
        'team1_golferB_scores': zip(team1_golferB_scores, team1_golferB_css),
        'team2_golferA_scores': zip(team2_golferA_scores, team2_golferA_css),
        'team2_golferB_scores': zip(team2_golferB_scores, team2_golferB_css),
        'team1_golferA_hole_points': team1_golferA_hole_points,
        'team1_golferB_hole_points': team1_golferB_hole_points,
        'team2_golferA_hole_points': team2_golferA_hole_points,
        'team2_golferB_hole_points': team2_golferB_hole_points,
        'team1_golferA_round_points': team1_golferA_round_points,
        'team1_golferB_round_points': team1_golferB_round_points,
        'team2_golferA_round_points': team2_golferA_round_points,
        'team2_golferB_round_points': team2_golferB_round_points,
        'team1_golferA_total_points': team1_golferA_total_points,
        'team1_golferB_total_points': team1_golferB_total_points,
        'team2_golferA_total_points': team2_golferA_total_points,
        'team2_golferB_total_points': team2_golferB_total_points,})
        
    
    # Render the template with the context
    context = {
        'week_number': week_number,
        'holes': holes,
        'hole_string': hole_string,
        'cards': cards,
    }
    
    return render(request, 'scorecards.html', context)

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