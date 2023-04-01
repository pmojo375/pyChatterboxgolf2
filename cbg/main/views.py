from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from main.models import *
from main.helper import *
from main.forms import *

# Create your views here.
def main(request):
    #week = get_week()
    season = Season.objects.get(year=2022)
    week = Week.objects.filter(season=season)[0]
    print(week.number)
    lastGameWinner = []

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

    if request.session.get('new', False):
        new_messages = []
        new = False
    else:
        new_messages = ['Sub Summary Pages: Now subs can see their summary pages like regular league members can!']
        new_messages.append('Handicaps are now rounded on the main page and week scorecard page.')
        new = True
        request.session['new'] = True

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
        'new': new,
        'new_messages': new_messages,
    }
    return render(request, 'main.html', context)


def add_round(request):
    if request.method == 'POST':
        golfer_id = request.POST['golfer']
        week_id = request.POST['week']

        golfer = Golfer.objects.get(id=golfer_id)
        week = Week.objects.get(id=week_id)

        if week.is_front:
            holes = range(1,10)
        else:
            holes = range(10,19)
        
        scores = []

        for i in holes:
            hole_number = i
            score_value = int(request.POST[f'hole{i}'])

            # Assuming holes are unique per season and week
            hole = Hole.objects.get(number=hole_number, season=week.season)

            score = Score(golfer=golfer, week=week, hole=hole, score=score_value)
            scores.append(score)

        # Save all score entries at once
        Score.objects.bulk_create(scores)

        messages.success(request, '9-hole round entry saved successfully.')
        return redirect('add_round')

    else:
        golfers = Golfer.objects.all()
        current_season = Season.objects.latest('year')
        current_season_weeks = Week.objects.filter(season=current_season)
        current_week = Week.objects.filter(season=current_season, date__lte=timezone.now()).latest('date')

        if current_week.is_front:
            holes = range(1,10)
        else:
            holes = range(10,19)

        context = {
            'golfers': golfers,
            'current_season_weeks': current_season_weeks,
            'current_week': current_week,
            'holes': holes
        }
        return render(request, 'add_round.html', context)
    

def add_golfer(request):
    if request.method == 'POST':
        name = request.POST['name']

        # Validate form data
        if not name:
            messages.error(request, 'All fields are required.')
            return redirect('add_golfer')

        # Save golfer data to the database
        golfer = Golfer(
            name=name,
        )
        golfer.save()
        messages.success(request, 'Golfer added successfully.')
        return redirect('add_golfer')

    return render(request, 'add_golfer.html')


def add_sub(request):

    if request.method == 'POST':
        absent_golfer_id = request.POST['absent_golfer']
        sub_golfer_id = request.POST['sub_golfer']
        week_id = request.POST['week']

        if absent_golfer_id == sub_golfer_id:
            messages.error(request, 'The absent golfer and the sub golfer cannot be the same person.')
            return redirect('add_sub')

        absent_golfer = Golfer.objects.get(id=absent_golfer_id)
        sub_golfer = Golfer.objects.get(id=sub_golfer_id)
        week = Week.objects.get(id=week_id)
        sub = Sub(
            absent_golfer=absent_golfer,
            sub_golfer=sub_golfer,
            week=week
        )
        sub.save()
        messages.success(request, 'Sub added successfully.')
        return redirect('add_sub')

    else:
        golfers = Golfer.objects.all()
        current_season = Season.objects.latest('year')
        current_season_weeks = Week.objects.filter(season=current_season)
        current_week = Week.objects.filter(season=current_season, date__lte=timezone.now()).latest('date')

        context = {
            'golfers': golfers,
            'current_season_weeks': current_season_weeks,
            'current_week': current_week
        }  
        return render(request, 'add_sub.html', context)
