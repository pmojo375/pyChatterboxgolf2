from datetime import timedelta
from main.models import *
from django.db.models import Sum
from django.utils import timezone
import random
import math

def conventional_round(value):
    """
    Conventional rounding: 0.5 and up round up, under 0.5 round down.
    This is different from Python's built-in round() which uses banker's rounding.
    """
    return math.floor(value + 0.5)

'''
Need to run the golfer matchup generator weekly. Need to figure out trigger
Need to figure out the handicap trigger for when the scores are posted and when to run a full generate
Need to figure out when to run the generate_rounds function
'''

def get_week(**kwargs):
    """Gets the week object from the current date. The week
    object returned is the last week we should have played but is offset by a
    week if no scores are posted for that week if the offset flag is not set to
    false.

    Parameters
    ----------
    offset : bool, optional
        A flag to offset if scores are not posted for returned week (default is
        True)
    season : Season, optional
        The season you want to get the week in (default is current season object)

    Returns
    -------
    Week
        The week object of the season requested offset by -1 if there are no
        posted scores.
    """

    # offset for returning the previous week if no scores are posted
    offset = kwargs.get('offset', True)
    # the year of the season you want
    season = kwargs.get('season', Season.objects.all().order_by('-year')[0])

    # current datetime
    now = timezone.now()

    # get week
    week = Week.objects.filter(date__lte=now).order_by('-date')[0]

    # offset by one week if not all scores are posted
    if offset:
        if Score.objects.filter(week=week).count() == 180:
            week = week
        else:
            week = Week.objects.filter(date__lte=now).order_by('-date')[1]

    return week

def get_game_winners(game):
    if GameEntry.objects.filter(winner=True, game=game).exists():
        winners = []
        for winner in GameEntry.objects.filter(winner=True, game=game):
            winners.append(winner.golfer.name)
        
        return winners
    else:
        return None

def get_game(week):
    """Get the game object for a given week

    Parameters
    ----------
    week : Week
        The week object you want to get the game for

    Returns
    -------
    Game
        The game object for the given week
    """

    # get the game object for the week
    if Game.objects.filter(week=week).exists():
        game = Game.objects.get(week=week)
    else:
        game = None

    return game

def get_current_season():
    """Gets the current season object from the current year

    Returns
    -------
    Season
        The current season object or False if no season exists
    """

    # get current date
    now = timezone.now()

    # get season if it exists
    if Season.objects.filter(year=2025).exists():
        season = Season.objects.get(year=2025)
    else:
        season = None

    return season


def get_last_week():

    print('Getting last week')
    # check if season exists
    current_season = get_current_season()
    
    if not current_season: 
        return None
    else:
        # get the latest week that was played before the current date
        weeks = Week.objects.filter(season=current_season, date__lt=timezone.now()).order_by('-date')
        
        for week in weeks:
            if Score.objects.filter(week=week).count() == week.num_scores:
                return week
            
        return None

def get_next_week():
    print('Getting next week')
    current_season = get_current_season()
    if not current_season:
        return None
    # Get all weeks in order (by number) starting from week 1
    weeks = Week.objects.filter(season=current_season).order_by('number')
    for week in weeks:
        if not week.rained_out:
            score_count = Score.objects.filter(week=week).count()
            # Find first week with 0 scores or fewer scores than expected
            if score_count == 0 or score_count < week.num_scores:
                print(f'Found next week: {week.number} (scores: {score_count}/{week.num_scores})')
                return week
    return None

def get_golfers(**kwargs):
    """Gets the golfer objects for a specific season

    Parameters
    ----------
    include_subs : boolean, optional
        Set True if you would like to also include subs in the lookup
        (default is false)
    season : Season, optional
        The season you want to get the week in (default is current season object)

    Returns
    -------
    QuerySet
        Returns a QuerySet of all the golfers for a season with our without subs
    """

    # get optional parameters
    subs = kwargs.get('include_subs', False)
    season = kwargs.get('season', Season.objects.all().order_by('-year')[0])

    if subs:
        return Golfer.objects.filter(sub__week__season=season).distinct().union(Golfer.objects.filter(team__season=season))
    else:
        return Golfer.objects.filter(team__season=season)


def get_sub(golfer, week):
    """Gets a sub object for an absent golfer

    Parameters
    ----------
    golfer : Golfer
        The absent golfer
    week : Week
        The week the golfer was absent

    Returns
    -------
    Golfer
        The sub's Golfer object or the original golfer object if there is no sub found
    """

    if Sub.objects.filter(absent_golfer=golfer, week=week).exists():
        if Sub.objects.get(absent_golfer=golfer, week=week).no_sub:
            return None
        else:
            return Sub.objects.get(absent_golfer=golfer, week=week).sub_golfer
    else:
        return golfer


def get_absent_team_from_sub(sub_golfer, week):
    """Gets the absent golfers team object from a sub golfer object

    Parameters
    ----------
    sub_golfer : Golfer
        The golfer subbing for the absent golfer
    week : Week, optional
        The week the sub played

    Returns
    -------
    Team
        The absent golfers team that the sub played for
    """

    return sub_golfer.sub.get(week=week).absent_golfer.team_set.get(season=week.season)


def generate_rounds(season):
    """
    Generate rounds for all weeks in a season that have been played.
    
    Parameters
    ----------
    season : Season
        The season to generate rounds for
        
    Returns
    -------
    int
        The number of rounds generated
    """
    # Get all weeks in the season that have scores (been played)
    weeks = Week.objects.filter(season=season).order_by('number')
    played_weeks = []
    for week in weeks:
        if Score.objects.filter(week=week).exists():
            played_weeks.append(week)
    
    total_rounds = 0
    
    # Generate rounds for each played week
    for week in played_weeks:
        golfer_matchups = GolferMatchup.objects.filter(week=week)
        
        for golfer_matchup in golfer_matchups:
            try:
                generate_round(golfer_matchup)
                total_rounds += 1
            except Exception as e:
                print(f"Error generating round for {golfer_matchup.golfer.name} in week {week.number}: {e}")
    
    return total_rounds


def generate_round(golfer_matchup, **kwargs):
    
    golfer = golfer_matchup.golfer
    week = golfer_matchup.week
    
    if golfer_played(golfer, week):
        gross_score = Score.objects.filter(golfer=golfer, week=week).aggregate(Sum('score'))['score__sum']
        handicap = Handicap.objects.get(golfer=golfer, week=week)
        net_score = gross_score - conventional_round(handicap.handicap)  # Use conventionally rounded handicap for net score
        scores = Score.objects.filter(golfer=golfer, week=week)
        is_sub = True if golfer_matchup.subbing_for_golfer else False
        if is_sub:
            matchup = Matchup.objects.get(week=week, teams__golfers__in=[golfer_matchup.subbing_for_golfer])
        else:
            matchup = Matchup.objects.get(week=week, teams__golfers__in=[golfer_matchup.golfer])
        points_detail = get_golfer_points(golfer_matchup, detail=True)
        round_points = points_detail['round_points']
        total_points = points_detail['golfer_points']
        # Get points objects AFTER calculating points
        points_objs = Points.objects.filter(golfer=golfer, week=week).order_by('hole__number')
        if Round.objects.filter(golfer=golfer, week=week, golfer_matchup=golfer_matchup).exists():
            round = Round.objects.get(golfer=golfer, week=week, golfer_matchup=golfer_matchup)
            round.handicap = handicap
            round.is_sub = is_sub
            round.gross = gross_score
            round.net = net_score
            round.golfer_matchup = golfer_matchup
            round.matchup = matchup
            round.round_points = round_points
            round.total_points = total_points
            if is_sub:
                round.subbing_for = golfer_matchup.subbing_for_golfer
            round.points.set(points_objs)
            round.scores.set(scores)
            round.save()
        else:
            round = Round(golfer=golfer, week=week, matchup=matchup, golfer_matchup=golfer_matchup, handicap=handicap, gross=gross_score, net=net_score, round_points=round_points, total_points=total_points, is_sub=is_sub)
            round.save()
            round.points.set(points_objs)
            if is_sub:
                round.subbing_for = golfer_matchup.subbing_for_golfer
            round.scores.set(scores)
            round.save()

    
def golfer_played(golfer, week, **kwargs):
    """Checks if a golfer played in a given week and year

    Parameters
    ----------
    golfer : Golfer
        The golfer object that you want to know if they played or not the given week
    week : Week
        The week object you are checking against

    Returns
    -------
    bool
        True or False depending on whether the golfer has any scores posted for
        the specified week and year.
    """

    return Score.objects.filter(golfer=golfer, week=week).exists()


def get_hcp(golfer, week):
    """Gets a golfers handicap for a specific week

    Parameters
    ----------
    golfer : Golfer
        The golfer that you want the handicap for.
    week : Week
        The week you want the golfers handicap for.

    Returns
    -------
    int
        The golfers handicap
    """

    try:
        return Handicap.objects.get(golfer=golfer, week=week).handicap
    except Handicap.DoesNotExist:
        return 0


# redo with new golfer matchup data
def get_schedule(week_model):
    """
    Given a week model, return the schedule of matches for that week.

    The schedule is returned as a list of lists, where each inner list represents a match and contains two sublists, one
    for the team with the lower handicap golfers and one for the team with the higher handicap golfers.

    :param week_model: The week model to retrieve the schedule for.
    :type week_model: cbg.main.models.Week
    :return: The schedule of matches for the given week.
    :rtype: List[List[List[str]]]
    """
    # Get all matches for the inputed week
    matches = week_model.matchup_set.all()
    schedule = []
    
    if matches.count() == 0:
        return None
    else:
        # Iterate through the matches and format the information for each match
        for match in matches:
            team1_golfer1 = match.teams.all()[0].golfers.all()[0]
            team1_golfer2 = match.teams.all()[0].golfers.all()[1]
            team2_golfer1 = match.teams.all()[1].golfers.all()[0]
            team2_golfer2 = match.teams.all()[1].golfers.all()[1]

            team1_golfer1_hcp = team1_golfer1.handicap_set.all().order_by('-week__date').first().handicap if team1_golfer1.handicap_set.all().order_by('-week__date').first() else 0
            team1_golfer2_hcp = team1_golfer2.handicap_set.all().order_by('-week__date').first().handicap if team1_golfer2.handicap_set.all().order_by('-week__date').first() else 0
            team2_golfer1_hcp = team2_golfer1.handicap_set.all().order_by('-week__date').first().handicap if team2_golfer1.handicap_set.all().order_by('-week__date').first() else 0
            team2_golfer2_hcp = team2_golfer2.handicap_set.all().order_by('-week__date').first().handicap if team2_golfer2.handicap_set.all().order_by('-week__date').first() else 0

            if team1_golfer1_hcp > team1_golfer2_hcp and team2_golfer1_hcp > team2_golfer2_hcp:
                match_low = [team1_golfer2.name, team2_golfer2.name]
                match_high = [team1_golfer1.name, team2_golfer1.name]
            elif team1_golfer1_hcp < team1_golfer2_hcp and team2_golfer1_hcp < team2_golfer2_hcp:
                match_low = [team1_golfer1.name, team2_golfer1.name]
                match_high = [team1_golfer2.name, team2_golfer2.name]
            elif team1_golfer1_hcp > team1_golfer2_hcp and team2_golfer1_hcp < team2_golfer2_hcp:
                match_low = [team1_golfer2.name, team2_golfer1.name]
                match_high = [team1_golfer1.name, team2_golfer2.name]
            else:
                match_low = [team1_golfer1.name, team2_golfer2.name]
                match_high = [team1_golfer2.name, team2_golfer1.name]

            schedule.append({'low_match': match_low, 'high_match': match_high})

        return schedule


def calculate_team_points(current_week):
    # Get the current season
    current_season = current_week.season

    # Get all the weeks for the current season up to the given week
    weeks = Week.objects.filter(season=current_season, number__lte=current_week.number)

    # Get all the teams in the current season
    teams = Team.objects.filter(season=current_season)

    # Initialize a dictionary to store team points
    team_points = {}

    # Iterate through the teams and calculate the total points for each team
    for team in teams:
        team_golfers = team.golfers.all()
        total_points = 0

        # Iterate through the weeks and calculate golfer points for each week
        for week in weeks:
            for golfer in team_golfers:
                # Get the golfer matchup for this golfer and week
                try:
                    golfer_matchup = GolferMatchup.objects.get(week=week, golfer=golfer)
                    golfer_points = get_golfer_points(golfer_matchup)
                    if isinstance(golfer_points, (int, float)):  # Only add points if the function returns a number
                        total_points += golfer_points
                except GolferMatchup.DoesNotExist:
                    # If no matchup exists for this golfer/week, skip it
                    continue

        # Store the team points in the dictionary
        team_points[team.id] = total_points

    return team_points
    
def get_front_holes(season):
    """
    Retrieve the front holes for a given season.

    Args:
        season (str): The season for which to retrieve the front holes.

    Returns:
        QuerySet: A queryset of Hole objects representing the front holes for the given season.
    """
    hole_numbers = range(1, 10)
    return Hole.objects.filter(season=season, number__in=hole_numbers).order_by('number')


def get_back_holes(season):
    """
    Retrieve the back holes for a given season.

    Args:
        season (str): The season for which to retrieve the back holes.

    Returns:
        QuerySet: A queryset of Hole objects representing the back holes for the given season.
    """
    hole_numbers = range(10, 19)
    return Hole.objects.filter(season=season, number__in=hole_numbers).order_by('number')


def get_golfer_points(golfer_matchup, **kwargs):
    """
    Calculate the points for a golfer in a matchup based on their scores, handicaps, and the week's holes.
    Args:
        golfer_matchup (object): An object representing the golfer's matchup, containing:
            - golfer: The golfer's model instance.
            - opponent: The opponent's model instance.
            - week: The week model instance.
            - is_teammate_subbing: Boolean indicating if this golfer is subbing for a teammate due to no_sub.
        **kwargs: Optional keyword arguments:
            - detail (bool): If True, returns a detailed dictionary of points for both the golfer and their opponent.
              Defaults to False.
    Returns:
        int or dict: 
            - If `detail` is False, returns the total points for the golfer as an integer.
            - If `detail` is True, returns a dictionary with the following keys:
                - 'golfer': The golfer's model instance.
                - 'golfer_points': Total points for the golfer.
                - 'opponent': The opponent's model instance.
                - 'opp_points': Total points for the opponent.
                - 'hole_points': Points earned by the golfer on individual holes.
                - 'opp_hole_points': Points earned by the opponent on individual holes.
                - 'round_points': Points earned by the golfer for the round.
                - 'opp_round_points': Points earned by the opponent for the round.
    Notes:
        - Points are calculated based on net scores (gross score minus handicap) for each hole.
        - Handicaps are applied to adjust scores based on the difference between the golfer's and opponent's handicaps.
        - Points are awarded for each hole and for the overall round:
            - 1 point for winning a hole, 0.5 points for tying a hole.
            - 3 points for winning the round, 1.5 points for tying the round.
        - When a golfer is subbing for a teammate due to no_sub, they automatically lose the 3 points for lowest net.
        - Points are stored or updated in the `Points` model for each hole.
    Raises:
        DoesNotExist: If a score for a specific hole is not found in the database.
    """
    
    # When detail is set to True, the function returns a dictionary with the points for the golfer and their opponent
    detail = kwargs.get('detail', False)
    
    # Get the golfers opponent
    opponent = golfer_matchup.opponent
    
    golfer_model = golfer_matchup.golfer
    week_model = golfer_matchup.week
    
    # Get all scores for the inputed week and golfer
    scores = Score.objects.filter(golfer=golfer_model, week=week_model)
    opp_scores = Score.objects.filter(golfer=opponent, week=week_model)
    
    # Get the golfers handicap and the opponents handicap
    golfer_hcp = get_hcp(golfer_model, week_model)
    opp_hcp = get_hcp(opponent, week_model)

    # ROUND EACH HANDICAP BEFORE SUBTRACTION
    rounded_golfer_hcp = conventional_round(golfer_hcp)
    rounded_opp_hcp = conventional_round(opp_hcp)

    gross_score = scores.aggregate(Sum('score'))['score__sum']
    opp_gross_score = opp_scores.aggregate(Sum('score'))['score__sum']

    net_score = gross_score - rounded_golfer_hcp  # Use rounded handicap for net score
    opp_net_score = opp_gross_score - rounded_opp_hcp  # Use rounded handicap for net score
    
    # Initialize the points to 0
    points = 0
    opp_points = 0
    
    # Figure out if the golfer is giving or getting strokes
    if rounded_golfer_hcp > rounded_opp_hcp:
        hcp_diff = rounded_golfer_hcp - rounded_opp_hcp
        getting = True
        giving = False
    elif rounded_golfer_hcp < rounded_opp_hcp:
        hcp_diff = rounded_opp_hcp - rounded_golfer_hcp
        getting = False
        giving = True
    else:
        hcp_diff = 0
        giving = False
        getting = False

    if hcp_diff > 9:
        hcp_diff = hcp_diff - 9
        rollover = 1
    else:
        rollover = 0

    # Get the holes for the inputed week
    if week_model.is_front:
        holes = get_front_holes(week_model.season)
    else:
        holes = get_back_holes(week_model.season)
    
    # Clear existing points for this golfer and week before calculating new ones
    Points.objects.filter(golfer=golfer_model, week=week_model).delete()
    Points.objects.filter(golfer=opponent, week=week_model).delete()
    
    # Iterate over the holes and calculate the points for each golfer
    for hole in holes:
        # Get the net scores for the inputed golfer and their opponent
        golfer_score_model = scores.get(hole=hole)
        opponent_score_model = opp_scores.get(hole=hole)
        golfer_score = golfer_score_model.score
        opponent_score = opponent_score_model.score
        
        original_golfer_score = golfer_score
        original_opponent_score = opponent_score
        
        # Apply handicaps
        if hole.handicap9 <= hcp_diff:
            if giving:
                opponent_score = opponent_score - (1 + rollover)
            if getting:
                golfer_score = golfer_score - (1 + rollover)
        elif rollover == 1:
            if giving:
                opponent_score = opponent_score - 1
            if getting:
                golfer_score = golfer_score - 1



        # Calculate the points for the hole based on the net scores
        if golfer_score < opponent_score:
            points += 1
            Points.objects.update_or_create(golfer=golfer_model, week=week_model, hole=hole, score=golfer_score_model, points=1)
            Points.objects.update_or_create(golfer=opponent, week=week_model, hole=hole, score=opponent_score_model, points=0)
        elif golfer_score == opponent_score:
            points += 0.5
            opp_points += 0.5
            Points.objects.update_or_create(golfer=golfer_model, week=week_model, hole=hole, score=golfer_score_model, points=0.5)
            Points.objects.update_or_create(golfer=opponent, week=week_model, hole=hole, score=opponent_score_model, points=0.5)
        else:
            opp_points += 1
            Points.objects.update_or_create(golfer=golfer_model, week=week_model, hole=hole, score=golfer_score_model, points=0)
            Points.objects.update_or_create(golfer=opponent, week=week_model, hole=hole, score=opponent_score_model, points=1)
        

    
    hole_points = points
    opp_hole_points = opp_points

    # Check if either golfer is subbing for a teammate due to no_sub
    golfer_is_teammate_subbing = golfer_matchup.is_teammate_subbing
    opponent_is_teammate_subbing = False
    
    # Check if opponent is also subbing for a teammate
    try:
        opponent_matchup = GolferMatchup.objects.get(week=week_model, golfer=opponent, opponent=golfer_model)
        opponent_is_teammate_subbing = opponent_matchup.is_teammate_subbing
    except GolferMatchup.DoesNotExist:
        pass

    # Calculate the points for the 9th hole based on the net scores
    # If either golfer is subbing for a teammate due to no_sub, they automatically lose the 3 points
    if golfer_is_teammate_subbing and opponent_is_teammate_subbing:
        # Both golfers are subbing for teammates - no one gets the 3 points
        round_points = 0
        opp_round_points = 0
    elif golfer_is_teammate_subbing:
        # Golfer is subbing for teammate - opponent gets the 3 points automatically
        opp_points += 3
        round_points = 0
        opp_round_points = 3
    elif opponent_is_teammate_subbing:
        # Opponent is subbing for teammate - golfer gets the 3 points automatically
        points += 3
        round_points = 3
        opp_round_points = 0
    else:
        # Normal case - calculate based on net scores
        if net_score < opp_net_score:
            points += 3
            round_points = 3
            opp_round_points = 0
        elif net_score == opp_net_score:
            points += 1.5
            round_points = 1.5
            opp_points += 1.5
            opp_round_points = 1.5
        else:
            opp_points += 3
            opp_round_points = 3
            round_points = 0

    if detail:
        return {'golfer': golfer_model, 'golfer_points': points, 'opponent': opponent, 'opp_points': opp_points, 'hole_points': hole_points, 'opp_hole_points': opp_hole_points, 'round_points': round_points, 'opp_round_points': opp_round_points}
    else:
        return points


def check_hcp():
    """
    Check handicap for each golfer and week combination.
    Prints the golfer's name, their recorded handicap, and the calculated handicap.
    """
    golfers = Golfer.objects.all()
    weeks = Week.objects.all()
    
    for golfer in golfers:
        for week in weeks:
            count = Handicap.objects.filter(golfer=golfer, week=week).count()
            if count > 1:
                handicaps = Handicap.objects.filter(golfer=golfer, week=week)
                for handicap in handicaps:
                    calc = calculate_handicap(golfer, week.season, week)
                    print(f'{golfer.name} has {handicap.handicap} handicap for {week.number} and calculated is {calc}')
        

def calculate_handicap(golfer, season, week):
    """
    Calculates the handicap for a given golfer for a given week in a given season.

    Parameters:
        golfer (Golfer): A Golfer instance representing the golfer for whom the handicap is being calculated.
        season (Season): A Season instance representing the season in which the handicap is being calculated.
        week (Week): A Week instance representing the week for which the handicap is being calculated.

    Returns:
        float: The calculated handicap for the given golfer, season, and week.

    """

    # Get the 10 most recent weeks in which the golfer played
    subquery = Score.objects.filter(golfer=golfer, week__season=season, week__date__lt=week.date).order_by('-week__date').values('week').distinct()[:10]

    # Get all the scores for the golfer in those 10 weeks
    scores = Score.objects.filter(golfer=golfer, week__in=subquery).order_by('-week__date')

    # gets the golfers on the teams for the season (exludes subs unless sub is a team member)
    normal_season_golfers = Golfer.objects.filter(team__season=season)

    # If there are scores for the golfer in the 10 most recent weeks, calculate the handicap
    if len(scores) != 0:
        # Group the scores by week
        scores_by_week = {}
        for score in scores:
            if score.week not in scores_by_week:
                scores_by_week[score.week] = []
            scores_by_week[score.week].append(score.score)

        # Sort the weeks by the sum of scores for each week
        weeks = sorted(scores_by_week.keys(), key=lambda week: sum(scores_by_week[week]))

        # Compute the handicap based on the number of weeks and whether to drop any
        num_weeks = len(weeks)
        if num_weeks < 5 or not golfer in normal_season_golfers:
            # If there are fewer than 5 weeks, use all the scores and subtract 36 (par) from each score
            handicap = (sum(score for scores in scores_by_week.values() for score in scores) / num_weeks - 36) * 0.8
        elif golfer in normal_season_golfers:
            # If there are 5 or more weeks, drop the highest- and lowest-scoring weeks and use the remaining scores
            drop_weeks = [weeks[0], weeks[-1]]
            scores = [score for week in weeks if week not in drop_weeks for score in scores_by_week[week]]
            handicap = (sum(scores) / (num_weeks - len(drop_weeks)) - 36) * 0.8

        return round(handicap, 5)
    else:
        return 0


def calculate_and_save_handicaps_for_season(season, weeks=None, golfers=None):
    """
    Calculate and save handicaps for a given season.

    Args:
        season (Season): The season for which to calculate and save handicaps.
        weeks (QuerySet, optional): The weeks in the season. If not provided, all weeks in the season will be used.
        golfers (QuerySet, optional): The golfers for whom to calculate and save handicaps. If not provided, all golfers who played in the season will be used.

    Returns:
        None
    """

    if golfers is None:
        # Get all the golfers who played in the season
        golfers = Golfer.objects.filter(score__week__season=season).distinct()

    # gets the golfers on the teams for the season (exludes subs unless sub is a team member)
    normal_season_golfers = Golfer.objects.filter(team__season=season)

    if weeks is None:
        # Get all the weeks in the season
        weeks = season.week_set.all().order_by('number')

    # Loop through each golfer and each week in the season
    for golfer in golfers:
        weeks_played = 0
        weeks_played_list = []
        backset_first_three = False
        for week in weeks:
            # Calculate the golfer's handicap for the week
            handicap = calculate_handicap(golfer, season, week)
            
            if golfer_played(golfer, week):
                weeks_played_list.append(week)
                weeks_played += 1

            # Save the calculated handicap in the database if it doesn't exist
            handicap_obj, created = Handicap.objects.get_or_create(golfer=golfer, week=week, defaults={'handicap': handicap})

            # Update the handicap if it already exists but has a different value
            if not created and handicap_obj.handicap != handicap:
                handicap_obj.handicap = handicap
                handicap_obj.save()

            # Update the first three weeks with the handicap calculated using the fourth week
            if weeks_played == 4 and not backset_first_three and golfer in normal_season_golfers:
                backset_first_three = True
                first_three_weeks = weeks_played_list[:3]
                for prev_week in first_three_weeks:
                    try:
                        handicap_obj = Handicap.objects.get(golfer=golfer, week=prev_week)
                        handicap_obj.handicap = handicap
                        handicap_obj.save()
                    except Handicap.DoesNotExist:
                        Handicap.objects.create(golfer=golfer, week=prev_week, handicap=handicap)   
        if weeks_played < 4 and golfer in normal_season_golfers:
            # If golfer didnt play 4 weeks yet, apply the handicap of their last round to the first 3 or less weeks of the season
            most_recent_handicap = Handicap.objects.filter(golfer=golfer).order_by('-week__date').first()
            for week in weeks_played_list:
                try:
                    handicap_obj = Handicap.objects.get(golfer=golfer, week=week)
                    handicap_obj.handicap = most_recent_handicap.handicap
                    handicap_obj.save()
                except Handicap.DoesNotExist:
                    Handicap.objects.create(golfer=golfer, week=week, handicap=most_recent_handicap.handicap)
        if not golfer in normal_season_golfers and weeks_played > 0:
            first_week = weeks_played_list[0]
            if weeks_played == 1:
                most_recent_handicap = Handicap.objects.filter(golfer=golfer, week__season=season).order_by('-week__date').first()
                try:
                    handicap_obj = Handicap.objects.get(golfer=golfer, week=first_week)
                    handicap_obj.handicap = most_recent_handicap.handicap
                    handicap_obj.save()
                except Handicap.DoesNotExist:
                    Handicap.objects.create(golfer=golfer, week=first_week, handicap=most_recent_handicap.handicap)  
            else:
                second_week = weeks_played_list[1]
                second_week_handicap = Handicap.objects.filter(golfer=golfer, week=second_week).first()
                try:
                    handicap_obj = Handicap.objects.get(golfer=golfer, week=first_week)
                    handicap_obj.handicap = second_week_handicap.handicap
                    handicap_obj.save()
                except Handicap.DoesNotExist:
                    Handicap.objects.create(golfer=golfer, week=first_week, handicap=second_week_handicap.handicap)   

def get_standings(season, week):
    """
    Get the standings for a given season and week.

    Args:
        season (Season): The season for which to get the standings.
        week (Week): The week for which to get the standings.

    Returns:
        List[Tuple[str
    """
    
    
def get_score_string(data, holes):
    
    rank = data['score'] - holes.get(number=data['hole']).par
    
    # Getting 2 strokes
    if data['handicap'] == -2:
        if rank == -2:
            rankStr = 'getting2-stroke_eagle'
        elif rank == -1:
            rankStr = 'getting2-stroke_birdie'
        elif rank == 0:
            rankStr = 'getting2-stroke_par'
        elif rank == 1:
            rankStr = 'getting2-stroke_bogey'
        else:
            rankStr = 'getting2-stroke_worst'
    # Getting 1 stroke
    elif data['handicap'] == -1:
        if rank == -2:
            rankStr = 'getting-stroke_eagle'
        elif rank == -1:
            rankStr = 'getting-stroke_birdie'
        elif rank == 0:
            rankStr = 'getting-stroke_par'
        elif rank == 1:
            rankStr = 'getting-stroke_bogey'
        else:
            rankStr = 'getting-stroke_worst'
    # Straight up
    else:
        if rank == -2:
            rankStr = 'eagle'
        elif rank == -1:
            rankStr = 'birdie'
        elif rank == 0:
            rankStr = 'par'
        elif rank == 1:
            rankStr = 'bogey'
        else:
            rankStr = 'worst'
    
    return rankStr

def adjust_weeks(rained_out_week):
    """
    Adjusts the week numbers and dates for subsequent weeks after a rained-out week
    and adds a new week at the end of the schedule.

    Args:
        rained_out_week (Week): The week instance that was rained out.

    Functionality:
        - Increments the week numbers and adjusts the dates for all weeks 
          that occur after the rained-out week.
        - Adds a new week at the end of the schedule with an incremented week 
          number and a date 7 days after the last week's date.

    Note:
        This function assumes that the `Week` model has `week_number` and `date` 
        fields and that the `Week.objects` manager provides `filter`, `latest`, 
        and `create` methods.
    """
    subsequent_weeks = Week.objects.filter(week_number__gt=rained_out_week.week_number)
    for week in subsequent_weeks:
        week.week_number += 1
        week.date += timedelta(days=7)
        week.save()
    # Add a new week at the end
    last_week_number = Week.objects.latest('week_number').week_number
    new_week_date = Week.objects.latest('date').date + timedelta(days=7)
    Week.objects.create(week_number=last_week_number+1, date=new_week_date)
    
def generate_golfer_matchups(week):
    """
    Generates golfer matchups for a given week by pairing golfers from opposing teams
    and handling substitutions for absent golfers.
    This function performs the following steps:
    1. Retrieves all matchups for the specified week.
    2. Deletes any existing golfer matchups for the week.
    3. Iterates through each matchup and retrieves the teams and their golfers.
    4. Checks for absent golfers and replaces them with substitutes or teammates.
    5. Calculates handicaps for each golfer.
    6. Assigns A and B golfers for each team based on their handicaps.
    7. Creates golfer matchups, ensuring the correct "subbing_for" field is set.
    8. Prints information about which golfers are subbing for absent players.
    Args:
        week (int): The week number for which golfer matchups are to be generated.
    Raises:
        Exception: If there are issues with retrieving or processing matchups, teams, or golfers.
    Models Used:
        - Matchup: Represents a matchup between two teams for a given week.
        - GolferMatchup: Represents a matchup between individual golfers.
        - Sub: Represents a substitution for an absent golfer.
    Helper Functions:
        - get_hcp(golfer, week): Retrieves the handicap for a golfer for the specified week.
    Notes:
        - The function assumes that each team has exactly two golfers.
        - If a golfer is absent and no substitute is available, their teammate may replace them.
        - A/B status is determined based on current playing golfers' handicaps (including subs) when there are subs.
        - A/B status is preserved based on original team golfers' handicaps when there is a no_sub situation.
    """
    matchups = Matchup.objects.filter(week=week)

    # delete all golfer matchups for the week
    GolferMatchup.objects.filter(week=week).delete()

    for matchup in matchups:
        teams = list(matchup.teams.all())
        
        # Skip matchups that don't have exactly 2 teams (might happen if signal fires before teams are added)
        if len(teams) != 2:
            print(f'Skipping matchup {matchup.id} - has {len(teams)} teams instead of 2')
            continue
            
        team1 = teams[0]
        team2 = teams[1]

        team1_golfers = list(team1.golfers.all())
        team2_golfers = list(team2.golfers.all())
        
        # Skip matchups where teams don't have exactly 2 golfers each
        if len(team1_golfers) != 2 or len(team2_golfers) != 2:
            print(f'Skipping matchup {matchup.id} - team1 has {len(team1_golfers)} golfers, team2 has {len(team2_golfers)} golfers')
            continue

        team1_golfer1 = team1_golfers[0]
        team1_golfer2 = team1_golfers[1]
        team2_golfer1 = team2_golfers[0]
        team2_golfer2 = team2_golfers[1]

        # Check if any golfers are absent and set sub details
        team1_golfer1_sub = Sub.objects.filter(week=week, absent_golfer=team1_golfer1).first()
        team1_golfer2_sub = Sub.objects.filter(week=week, absent_golfer=team1_golfer2).first()
        team2_golfer1_sub = Sub.objects.filter(week=week, absent_golfer=team2_golfer1).first()
        team2_golfer2_sub = Sub.objects.filter(week=week, absent_golfer=team2_golfer2).first()
        
        team1_golfer1_has_no_sub = False
        team1_golfer2_has_no_sub = False
        team2_golfer1_has_no_sub = False
        team2_golfer2_has_no_sub = False

        # Store original golfers for A/B determination
        team1_original_golfer1 = team1_golfer1
        team1_original_golfer2 = team1_golfer2
        team2_original_golfer1 = team2_golfer1
        team2_original_golfer2 = team2_golfer2

        # Replace absent golfers with subs or teammates
        if team1_golfer1_sub:
            if team1_golfer1_sub.no_sub:
                team1_golfer1_has_no_sub = True
                team1_golfer1 = team1_golfer2  # Replace with teammate
                team1_golfer1_subbing_for = team1_golfer1_sub.absent_golfer  # Set subbing for absent golfer
            else:
                team1_golfer1 = team1_golfer1_sub.sub_golfer
                team1_golfer1_subbing_for = team1_golfer1_sub.absent_golfer
        else:
            team1_golfer1_subbing_for = None

        if team1_golfer2_sub:
            if team1_golfer2_sub.no_sub:
                team1_golfer2_has_no_sub = True
                team1_golfer2 = team1_golfer1  # Replace with teammate
                team1_golfer2_subbing_for = team1_golfer2_sub.absent_golfer
            else:
                team1_golfer2 = team1_golfer2_sub.sub_golfer
                team1_golfer2_subbing_for = team1_golfer2_sub.absent_golfer
        else:
            team1_golfer2_subbing_for = None

        if team2_golfer1_sub:
            if team2_golfer1_sub.no_sub:
                team2_golfer1_has_no_sub = True
                team2_golfer1 = team2_golfer2  # Replace with teammate
                team2_golfer1_subbing_for = team2_golfer1_sub.absent_golfer
            else:
                team2_golfer1 = team2_golfer1_sub.sub_golfer
                team2_golfer1_subbing_for = team2_golfer1_sub.absent_golfer
        else:
            team2_golfer1_subbing_for = None

        if team2_golfer2_sub:
            if team2_golfer2_sub.no_sub:
                team2_golfer2_has_no_sub = True
                team2_golfer2 = team2_golfer1  # Replace with teammate
                team2_golfer2_subbing_for = team2_golfer2_sub.absent_golfer
            else:
                team2_golfer2 = team2_golfer2_sub.sub_golfer
                team2_golfer2_subbing_for = team2_golfer2_sub.absent_golfer
        else:
            team2_golfer2_subbing_for = None

        # Determine A/B status based on whether there are subs or no_sub situations
        team1_has_no_sub = team1_golfer1_has_no_sub or team1_golfer2_has_no_sub
        team2_has_no_sub = team2_golfer1_has_no_sub or team2_golfer2_has_no_sub
        
        if team1_has_no_sub:
            # If team1 has a no_sub situation, preserve original A/B based on original team golfers
            team1_original_golfer1_hcp = get_hcp(team1_original_golfer1, week)
            team1_original_golfer2_hcp = get_hcp(team1_original_golfer2, week)
            
            if team1_original_golfer1_hcp <= team1_original_golfer2_hcp:
                team1_A_golfer, team1_B_golfer = team1_golfer1, team1_golfer2
                team1_A_subbing_for = team1_golfer1_subbing_for
                team1_B_subbing_for = team1_golfer2_subbing_for
                team1_A_has_no_sub = team1_golfer1_has_no_sub
                team1_B_has_no_sub = team1_golfer2_has_no_sub
            else:
                team1_A_golfer, team1_B_golfer = team1_golfer2, team1_golfer1
                team1_A_subbing_for = team1_golfer2_subbing_for
                team1_B_subbing_for = team1_golfer1_subbing_for
                team1_A_has_no_sub = team1_golfer2_has_no_sub
                team1_B_has_no_sub = team1_golfer1_has_no_sub
        else:
            # If team1 has subs, use current playing golfers' handicaps
            team1_golfer1_hcp = get_hcp(team1_golfer1, week)
            team1_golfer2_hcp = get_hcp(team1_golfer2, week)
            
            if team1_golfer1_hcp <= team1_golfer2_hcp:
                team1_A_golfer, team1_B_golfer = team1_golfer1, team1_golfer2
                team1_A_subbing_for = team1_golfer1_subbing_for
                team1_B_subbing_for = team1_golfer2_subbing_for
                team1_A_has_no_sub = team1_golfer1_has_no_sub
                team1_B_has_no_sub = team1_golfer2_has_no_sub
            else:
                team1_A_golfer, team1_B_golfer = team1_golfer2, team1_golfer1
                team1_A_subbing_for = team1_golfer2_subbing_for
                team1_B_subbing_for = team1_golfer1_subbing_for
                team1_A_has_no_sub = team1_golfer2_has_no_sub
                team1_B_has_no_sub = team1_golfer1_has_no_sub

        if team2_has_no_sub:
            # If team2 has a no_sub situation, preserve original A/B based on original team golfers
            team2_original_golfer1_hcp = get_hcp(team2_original_golfer1, week)
            team2_original_golfer2_hcp = get_hcp(team2_original_golfer2, week)
            
            if team2_original_golfer1_hcp <= team2_original_golfer2_hcp:
                team2_A_golfer, team2_B_golfer = team2_golfer1, team2_golfer2
                team2_A_subbing_for = team2_golfer1_subbing_for
                team2_B_subbing_for = team2_golfer2_subbing_for
                team2_A_has_no_sub = team2_golfer1_has_no_sub
                team2_B_has_no_sub = team2_golfer2_has_no_sub
            else:
                team2_A_golfer, team2_B_golfer = team2_golfer2, team2_golfer1
                team2_A_subbing_for = team2_golfer2_subbing_for
                team2_B_subbing_for = team2_golfer1_subbing_for
                team2_A_has_no_sub = team2_golfer2_has_no_sub
                team2_B_has_no_sub = team2_golfer1_has_no_sub
        else:
            # If team2 has subs, use current playing golfers' handicaps
            team2_golfer1_hcp = get_hcp(team2_golfer1, week)
            team2_golfer2_hcp = get_hcp(team2_golfer2, week)
            
            if team2_golfer1_hcp <= team2_golfer2_hcp:
                team2_A_golfer, team2_B_golfer = team2_golfer1, team2_golfer2
                team2_A_subbing_for = team2_golfer1_subbing_for
                team2_B_subbing_for = team2_golfer2_subbing_for
                team2_A_has_no_sub = team2_golfer1_has_no_sub
                team2_B_has_no_sub = team2_golfer2_has_no_sub
            else:
                team2_A_golfer, team2_B_golfer = team2_golfer2, team2_golfer1
                team2_A_subbing_for = team2_golfer2_subbing_for
                team2_B_subbing_for = team2_golfer1_subbing_for
                team2_A_has_no_sub = team2_golfer2_has_no_sub
                team2_B_has_no_sub = team2_golfer1_has_no_sub

        # Create golfer matchups, setting the subbing_for field correctly
        GolferMatchup.objects.create(week=week, golfer=team1_A_golfer, is_A=True, opponent=team2_A_golfer, subbing_for_golfer=team1_A_subbing_for, is_teammate_subbing=team1_A_has_no_sub)
        GolferMatchup.objects.create(week=week, golfer=team2_A_golfer, is_A=True, opponent=team1_A_golfer, subbing_for_golfer=team2_A_subbing_for, is_teammate_subbing=team2_A_has_no_sub)
        GolferMatchup.objects.create(week=week, golfer=team1_B_golfer, is_A=False, opponent=team2_B_golfer, subbing_for_golfer=team1_B_subbing_for, is_teammate_subbing=team1_B_has_no_sub)
        GolferMatchup.objects.create(week=week, golfer=team2_B_golfer, is_A=False, opponent=team1_B_golfer, subbing_for_golfer=team2_B_subbing_for, is_teammate_subbing=team2_B_has_no_sub)
        
        # print subbing for golfers
        print(f'{team1_A_golfer.name} is subbing for {team1_A_subbing_for.name}') if team1_A_subbing_for else print(f'{team1_A_golfer.name} is not subbing')
        print(f'{team2_A_golfer.name} is subbing for {team2_A_subbing_for.name}') if team2_A_subbing_for else print(f'{team2_A_golfer.name} is not subbing')
        print(f'{team1_B_golfer.name} is subbing for {team1_B_subbing_for.name}') if team1_B_subbing_for else print(f'{team1_B_golfer.name} is not subbing')
        print(f'{team2_B_golfer.name} is subbing for {team2_B_subbing_for.name}') if team2_B_subbing_for else print(f'{team2_B_golfer.name} is not subbing')

def process_week(week):
    
    # generate the handicaps for the next week
    calculate_and_save_handicaps_for_season(week.season)

    generate_golfer_matchups(week)
    
    # get the golfer matchups for the week
    golfer_matchups = GolferMatchup.objects.filter(week=week)

    for golfer_matchup in golfer_matchups:
        generate_round(golfer_matchup)
        
        
def get_playing_golfers_for_week(week):
    """
    Get all golfers who are actually playing in a given week (including subs)
    """
    playing_golfers = set()
    # Get all teams for the season
    teams = Team.objects.filter(season=week.season)
    for team in teams:
        team_golfers = team.golfers.all()
        for golfer in team_golfers:
            # Check if golfer is playing (not absent or has a sub)
            sub = Sub.objects.filter(week=week, absent_golfer=golfer).first()
            if not sub or (sub and sub.sub_golfer):
                # Golfer is playing (either directly or via sub)
                if sub and sub.sub_golfer:
                    playing_golfers.add(sub.sub_golfer)  # Add the sub
                else:
                    playing_golfers.add(golfer)  # Add the original golfer
    return list(playing_golfers)
    
def get_earliest_week_without_full_matchups(season=None):
    """
    Find the earliest week that doesn't have 5 matchups (full schedule).
    A full schedule typically has 5 matchups for a league with 10 teams.
    
    Args:
        season (Season, optional): The season to check. Defaults to current season.
    
    Returns:
        Week: The earliest week without 5 matchups, or None if all weeks are full
    """
    if season is None:
        season = get_current_season()
    
    if not season:
        return None
    
    # Get all weeks for the season ordered by week number
    weeks = Week.objects.filter(season=season, rained_out=False).order_by('number')
    
    for week in weeks:
        matchup_count = Matchup.objects.filter(week=week).count()
        if matchup_count < 5:  # Assuming 5 matchups is a full schedule
            return week
    
    return None  # All weeks have full matchups
    
        
    