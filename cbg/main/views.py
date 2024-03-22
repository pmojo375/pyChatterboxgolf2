from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from main.models import *
from main.signals import *
from main.helper import *
from main.forms import *
from django.contrib import messages
from django.db.models import Q, Sum
from datetime import datetime
from django.http import HttpResponseRedirect
import json

# Create your views here.
def main(request):
    #week = get_week()
    season = Season.objects.get(year=2022)
    week = Week.objects.filter(season=season)[0]
    print(week.number)
    lastGameWinner = []
    
    #calculate_and_save_handicaps_for_season(season)
    #generate_rounds(season)
    # sub records for the given year
    #subs = Subrecord.objects.filter(year=2022).values('sub_id', 'absent_id', 'week')

    if week.number > 8:
        secondHalf = True
    else:
        secondHalf = False

    seeds = []

    # get the next weeks schedule
    schedule = get_schedule(week)

    # check if there are handicaps for the given week
    check = Handicap.objects.filter(week=week).exists()

    # if the week is not the first of the year and there are not handicaps decrement the week
    if week != 0:
        #lastSkinWinner = get_skins_winner(week, year=2022)
        lastSkinWinner = []
        lastGame = Game.objects.get(week=week)
        if not check:
            week = week - 1
    else:
        lastGame = Game.objects.get(year=2021, week=19)
        lastSkinWinner = []

    # get standings for the current week
    #standings = getStandings(week)
    #standings = get_standings_fast(week, subs=subs, year=2022)

    # get standings in correct order
    #firstHalfStandings = sorted(standings, key=itemgetter('first'), reverse=True)
    #secondHalfStandings = sorted(standings, key=itemgetter('second'), reverse=True)
    #fullStandings = sorted(standings, key=itemgetter('total'), reverse=True)

    currentGame = Game.objects.get(week=week)

    if GameEntry.objects.filter(winner=True, week=week).exists():
        winners =  GameEntry.objects.filter(winner=True, week=week)
        for winner in winners:
                lastGameWinner.append(winner.golfer.name)
    else:
        lastGameWinner.append('Not Set')

    game_pot = (GameEntry.objects.filter(week=week).count() * 2)/len(lastGameWinner)

    season = Season.objects.all().order_by('-year')[0]
    golfer_list = Golfer.objects.filter(team__season=season)
    context = {
        'lastSkinWinner': lastSkinWinner,
        'week': week.number,
        'lastweek': week,
        'currentGame': currentGame,
        'lastGame': lastGame,
        'lastGameWinner': lastGameWinner,
        'game_pot': game_pot,
        'firstHalfStandings': [],
        'secondHalfStandings': [],
        'fullStandings': [],
        'schedule': schedule,
        'secondHalf': secondHalf,
        'unestablished': [],
        'golfer_list': golfer_list,
    }
    return render(request, 'main.html', context)

def add_scores(request):
    '''
    golfers = Golfer.objects.all()
    weeks = Week.objects.filter(season=Season.objects.order_by('-year').first()).order_by('-date')

    if request.method == 'POST':
        form = ScoresForm(golfers, weeks, request.POST)
        if form.is_valid():
            print('Valid Form\n')
            
            # Get form data
            golfer_id = form.cleaned_data['golfer']
            week_id = form.cleaned_data['week']
            scores = []
            for hole in range(1, 10):
                scores.append(form.cleaned_data[f'hole{hole}'])
                
            # Get the golfer and week objects
            golfer = Golfer.objects.get(id=golfer_id)
            week = Week.objects.get(id=week_id)
            
            # Get the holes for the week
            if week.is_front:
                holes_nums = range(1,10)
            else:
                holes_nums = range(10,19)
            
            # Create the score objects
            for index, score in enumerate(scores):
                hole = Hole.objects.get(number=holes_nums[index], season=week.season)
                score = Score(
                    golfer=golfer,
                    week=week,
                    hole=hole,
                    score=score
                )
                
                # Print info for debugging
                print(f'Golfer: {golfer.name}')
                print(f'Week: {week}')
                print(f'Hole: {hole.number}')
                print(f'Score: {score.score}')
                
                #score.save()
        else:
            print('Invalid Form\n')
            print(form.errors)
            
    else:
        form = ScoresForm(golfers, weeks)

    return render(request, 'add_round.html', {'form': form})
    '''
    if request.method == 'POST':
        
        form = RoundForm(request.POST)
        if form.is_valid():
            print('Valid Form\n')
            
            # Get form data
            matchup = int(form.cleaned_data['matchup'])
            print(form.golfer_data)
            print(f"{Golfer.objects.get(id=form.golfer_data[matchup][0][1])} - Hole 1 = {form.cleaned_data['hole1_1']}")
        else:
            print('Invalid Form\n')
            print(form.errors)
            
    else:
        form = RoundForm()
    
    golfer_data_json = json.dumps(form.golfer_data)

    return render(request, 'add_round.html', {'form': form, 'golfer_data_json': golfer_data_json})
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
            
            #golfer.save()
        else:
            print('Invalid Form\n')
            print(form.errors)
    else:
        form = GolferForm()
    
    return render(request, 'add_golfer.html', {'form': form})

def add_sub(request):
    absent_golfers = Golfer.objects.filter(team__season=Season.objects.order_by('-year').first())
    sub_golfers = Golfer.objects.exclude(team__season=Season.objects.order_by('-year').first())
    weeks = Week.objects.filter(season=Season.objects.order_by('-year').first()).order_by('-date')
    
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
            
            #sub.save()
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