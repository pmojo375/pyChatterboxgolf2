from django.shortcuts import render, redirect
from main.models import *
from main.signals import *
from main.helper import *
from main.forms import *
from django.db.models import Sum, Q
from main.season import *
from django.forms import formset_factory
from django.http import HttpResponseBadRequest

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

        return redirect('add_round.html', week=week.number)

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
    opponent_hcp = golfer_matchup.opponent.handicap_set.filter(week=week).first()
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
        
        if week_id:
            try:
                week = Week.objects.get(id=week_id)
                
                # First, ensure handicaps are calculated for the season
                calculate_and_save_handicaps_for_season(week.season)
                
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