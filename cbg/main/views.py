from django.shortcuts import render
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
    # if this is a POST request we need to process the form data
    if request.method == 'POST':
        # create a form instance and populate it with data from the request:
        form = RoundForm(request.POST)

        if form.is_valid():

            # determine if playing front or back
            isFront = week=form.cleaned_data['week'].is_front

            # set the appropriate hole array
            if isFront:
                hole_nums = [1, 2, 3, 4, 5, 6, 7, 8, 9]
            else:
                hole_nums = [10, 11, 12, 13, 14, 15, 16, 17, 18]
                
            holes = Hole.objects.filter(number__in=hole_nums)

            # golfer played alone and had no partner
            self_sub = form.cleaned_data['self_sub']

            if not Score.objects.all().filter(golfer=form.cleaned_data['golfer'], week=form.cleaned_data['week'], hole=holes.get(number__in=(1, 10))).exists():
                Score.objects.update_or_create(
                    golfer=form.cleaned_data['golfer'],
                    hole=holes.get(number__in=(1, 10)),
                    score=form.cleaned_data['hole1'],
                    week=form.cleaned_data['week']
                )
            if not Score.objects.all().filter(golfer=form.cleaned_data['golfer'], week=form.cleaned_data['week'], hole=holes.get(number__in=(2, 11))).exists():
                Score.objects.update_or_create(
                    golfer=form.cleaned_data['golfer'],
                    hole=holes.get(number__in=(2, 11)),
                    score=form.cleaned_data['hole2'],
                    week=form.cleaned_data['week']
                )
            if not Score.objects.all().filter(golfer=form.cleaned_data['golfer'], week=form.cleaned_data['week'], hole=holes.get(number__in=(3, 12))).exists():
                Score.objects.update_or_create(
                    golfer=form.cleaned_data['golfer'],
                    hole=holes.get(number__in=(3, 12)),
                    score=form.cleaned_data['hole3'],
                    week=form.cleaned_data['week']
                )
            if not Score.objects.all().filter(golfer=form.cleaned_data['golfer'], week=form.cleaned_data['week'], hole=holes.get(number__in=(4, 13))).exists():
                Score.objects.update_or_create(
                    golfer=form.cleaned_data['golfer'],
                    hole=holes.get(number__in=(4, 13)),
                    score=form.cleaned_data['hole4'],
                    week=form.cleaned_data['week']
                )
            if not Score.objects.all().filter(golfer=form.cleaned_data['golfer'], week=form.cleaned_data['week'], hole=holes.get(number__in=(5, 14))).exists():
                Score.objects.update_or_create(
                    golfer=form.cleaned_data['golfer'],
                    hole=holes.get(number__in=(5, 14)),
                    score=form.cleaned_data['hole5'],
                    week=form.cleaned_data['week']
                )
            if not Score.objects.all().filter(golfer=form.cleaned_data['golfer'], week=form.cleaned_data['week'], hole=holes.get(number__in=(6, 15))).exists():
                Score.objects.update_or_create(
                    golfer=form.cleaned_data['golfer'],
                    hole=holes.get(number__in=(6, 15)),
                    score=form.cleaned_data['hole6'],
                    week=form.cleaned_data['week']
                )
            if not Score.objects.all().filter(golfer=form.cleaned_data['golfer'], week=form.cleaned_data['week'], hole=holes.get(number__in=(7, 16))).exists():
                Score.objects.update_or_create(
                    golfer=form.cleaned_data['golfer'],
                    hole=holes.get(number__in=(7, 16)),
                    score=form.cleaned_data['hole7'],
                    week=form.cleaned_data['week']
                )
            if not Score.objects.all().filter(golfer=form.cleaned_data['golfer'], week=form.cleaned_data['week'], hole=holes.get(number__in=(8, 17))).exists():
                Score.objects.update_or_create(
                    golfer=form.cleaned_data['golfer'],
                    hole=holes.get(number__in=(8, 17)),
                    score=form.cleaned_data['hole8'],
                    week=form.cleaned_data['week']
                )
            if not Score.objects.all().filter(golfer=form.cleaned_data['golfer'], week=form.cleaned_data['week'], hole=holes.get(number__in=(9, 18))).exists():
                Score.objects.update_or_create(
                    golfer=form.cleaned_data['golfer'],
                    hole=holes.get(number__in=(9, 18)),
                    score=form.cleaned_data['hole9'],
                    week=form.cleaned_data['week']
                )
            """
            if self_sub:
                # the golfer with playing as both partners
                golfer_main = Golfer.objects.get(id=form.cleaned_data['golfer'])
                golfer_name = golfer_main.name

                # if the golfer playing solo is a sub already
                if golfer_main.team <= 0:

                    golfers = get_team_golfers(get_absents_team(golfer_main.id, form.cleaned_data['week'], year=form.cleaned_data['year']), week=form.cleaned_data['week'])

                    try:
                        golfer = Golfer.objects.get(name=golfer_name, year=form.cleaned_data['year'], team=golfer_main.team-1)
                    except Golfer.DoesNotExist:
                        golfer = Golfer(name=golfer_name, year=form.cleaned_data['year'], team=golfer_main.team-1)
                        golfer.save()
                else:

                    golfers = get_team_golfers(golfer_main.team, week=form.cleaned_data['week'])

                    try:
                        golfer = Golfer.objects.get(name=golfer_name, year=form.cleaned_data['year'], team=0)
                    except Golfer.DoesNotExist:
                        golfer = Golfer(name=golfer_name, year=form.cleaned_data['year'], team=0)
                        golfer.save()

                if not Score.objects.all().filter(golfer=golfer, week=form.cleaned_data['week'],
                                                  hole=holes[0], year=form.cleaned_data['year']).exists():
                    Score.objects.update_or_create(
                        golfer=golfer.id,
                        hole=holes[0],
                        score=form.cleaned_data['hole1'],
                        tookMax=form.cleaned_data['tookMax1'],
                        week=form.cleaned_data['week'],
                        year=form.cleaned_data['year']
                    )
                if not Score.objects.all().filter(golfer=golfer, week=form.cleaned_data['week'],
                                                  hole=holes[1], year=form.cleaned_data['year']).exists():
                    Score.objects.update_or_create(
                        golfer=golfer.id,
                        hole=holes[1],
                        score=form.cleaned_data['hole2'],
                        tookMax=form.cleaned_data['tookMax2'],
                        week=form.cleaned_data['week'],
                        year=form.cleaned_data['year']
                    )
                if not Score.objects.all().filter(golfer=golfer.id, week=form.cleaned_data['week'],
                                                  hole=holes[2], year=form.cleaned_data['year']).exists():
                    Score.objects.update_or_create(
                        golfer=golfer.id,
                        hole=holes[2],
                        score=form.cleaned_data['hole3'],
                        tookMax=form.cleaned_data['tookMax3'],
                        week=form.cleaned_data['week'],
                        year=form.cleaned_data['year']
                    )
                if not Score.objects.all().filter(golfer=golfer.id, week=form.cleaned_data['week'],
                                                  hole=holes[3], year=form.cleaned_data['year']).exists():
                    Score.objects.update_or_create(
                        golfer=golfer.id,
                        hole=holes[3],
                        score=form.cleaned_data['hole4'],
                        tookMax=form.cleaned_data['tookMax4'],
                        week=form.cleaned_data['week'],
                        year=form.cleaned_data['year']
                    )
                if not Score.objects.all().filter(golfer=golfer.id, week=form.cleaned_data['week'],
                                                  hole=holes[4], year=form.cleaned_data['year']).exists():
                    Score.objects.update_or_create(
                        golfer=golfer.id,
                        hole=holes[4],
                        score=form.cleaned_data['hole5'],
                        tookMax=form.cleaned_data['tookMax5'],
                        week=form.cleaned_data['week'],
                        year=form.cleaned_data['year']
                    )
                if not Score.objects.all().filter(golfer=golfer.id, week=form.cleaned_data['week'],
                                                  hole=holes[5], year=form.cleaned_data['year']).exists():
                    Score.objects.update_or_create(
                        golfer=golfer.id,
                        hole=holes[5],
                        score=form.cleaned_data['hole6'],
                        tookMax=form.cleaned_data['tookMax6'],
                        week=form.cleaned_data['week'],
                        year=form.cleaned_data['year']
                    )
                if not Score.objects.all().filter(golfer=golfer.id, week=form.cleaned_data['week'],
                                                  hole=holes[6], year=form.cleaned_data['year']).exists():
                    Score.objects.update_or_create(
                        golfer=golfer.id,
                        hole=holes[6],
                        score=form.cleaned_data['hole7'],
                        tookMax=form.cleaned_data['tookMax7'],
                        week=form.cleaned_data['week'],
                        year=form.cleaned_data['year']
                    )
                if not Score.objects.all().filter(golfer=golfer.id, week=form.cleaned_data['week'],
                                                  hole=holes[7], year=form.cleaned_data['year']).exists():
                    Score.objects.update_or_create(
                        golfer=golfer.id,
                        hole=holes[7],
                        score=form.cleaned_data['hole8'],
                        tookMax=form.cleaned_data['tookMax8'],
                        week=form.cleaned_data['week'],
                        year=form.cleaned_data['year']
                    )
                if not Score.objects.all().filter(golfer=golfer.id, week=form.cleaned_data['week'],
                                                  hole=holes[8], year=form.cleaned_data['year']).exists():
                    Score.objects.update_or_create(
                        golfer=golfer.id,
                        hole=holes[8],
                        score=form.cleaned_data['hole9'],
                        tookMax=form.cleaned_data['tookMax9'],
                        week=form.cleaned_data['week'],
                        year=form.cleaned_data['year']
                    )

                if golfers['A'].id == golfer_main.id:
                    partner = golfers['B']
                else:
                    partner = golfers['A']

                Subrecord(week=form.cleaned_data['week'], absent_id=partner.id, sub_id=golfer.id, year=form.cleaned_data['year']).save()

            """
            # redirect to a new URL:
            return HttpResponseRedirect('/addround/')
            pass

    # if a GET (or any other method) we'll create a blank form
    else:
        form = RoundForm()

    return render(request, 'addRound.html', {'form': form})