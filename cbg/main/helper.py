from datetime import datetime, timedelta
from main.models import *
from django.db.models import Max


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
    now = datetime.now()

    # get week
    week = Week.objects.filter(date__lte=now).order_by('-date')[0]

    # offset by one week if not all scores are posted
    if offset:
        if Score.objects.filter(week=week).count() == 180:
            week = week
        else:
            week = Week.objects.filter(date__lte=now).order_by('-date')[1]

    return week


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


def get_sub(golfer, week, **kwargs):
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

    try:
        return Sub.objects.get(absent_golfer=golfer, week=week).sub_golfer
    except Sub.DoesNotExist:
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


def golferPlayed(golfer, week, **kwargs):
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


def getHcp(golfer, week):
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

from typing import List

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
    subquery = Score.objects.filter(golfer=golfer, week__season=season, week__date__lte=week.date).order_by('-week__date').values('week').distinct()[:10]

    # Get all the scores for the golfer in those 10 weeks
    scores = Score.objects.filter(golfer=golfer, week__in=subquery).order_by('-week__date')

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
    if num_weeks < 5:
        # If there are fewer than 5 weeks, use all the scores and subtract 36 (par) from each score
        handicap = (sum(score for scores in scores_by_week.values() for score in scores) / num_weeks - 36) * 0.8
    else:
        # If there are 5 or more weeks, drop the highest- and lowest-scoring weeks and use the remaining scores
        drop_weeks = [weeks[0], weeks[-1]]
        scores = [score for week in weeks if week not in drop_weeks for score in scores_by_week[week]]
        handicap = (sum(scores) / (num_weeks - len(drop_weeks)) - 36) * 0.8

    return round(handicap, 2)

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
    # Iterate through the matches and format the information for each match
    for match in matches:
        team1_golfer1 = match.teams.all()[0].golfers.all()[0]
        team1_golfer2 = match.teams.all()[0].golfers.all()[1]
        team2_golfer1 = match.teams.all()[1].golfers.all()[0]
        team2_golfer2 = match.teams.all()[1].golfers.all()[1]

        team1_golfer1_hcp = team1_golfer1.handicap_set.all().order_by('-week__date')[0].handicap
        team1_golfer2_hcp = team1_golfer2.handicap_set.all().order_by('-week__date')[0].handicap
        team2_golfer1_hcp = team2_golfer1.handicap_set.all().order_by('-week__date')[0].handicap
        team2_golfer2_hcp = team2_golfer2.handicap_set.all().order_by('-week__date')[0].handicap

        if team1_golfer1_hcp > team1_golfer2_hcp and team2_golfer1_hcp > team2_golfer2_hcp:
            match_low = [team1_golfer2.name, team2_golfer2.name]
            match_high = [team1_golfer1.name, team2_golfer1.name]
        elif team1_golfer1_hcp < team1_golfer2_hcp and team2_golfer1_hcp < team2_golfer2_hcp:
            match_low = [team1_golfer1.name, team2_golfer1.name]
            match_high = [team1_golfer2.name, team2_golfer2.name]
        elif team1_golfer1_hcp > team1_golfer2_hcp and team2_golfer1_hcp < team2_golfer2_hcp:
            match_low = [team1_golfer2.name, team2_golfer1.name]
            match_high = [team1_golfer1.name, team2_golfer2.name]
        elif team1_golfer1_hcp < team1_golfer2_hcp and team2_golfer1_hcp > team2_golfer2_hcp:
            match_low = [team1_golfer1.name, team2_golfer2.name]
            match_high = [team1_golfer2.name, team2_golfer1.name]

        schedule.append([match_low, match_high])

    return schedule


from django.db.models import Q

def get_golfer_points(week_model, golfer_model, **kwargs):
    """
    Calculates the total points earned by the inputed golfer for the inputed week.
    The golfer points are calculated using the rules of the league's point system.

    Args:
        week_model (Week): Week model instance.
        golfer_model (Golfer): Golfer model instance.
        **kwargs: Additional keyword arguments.
            detail (bool, optional): If True, return a dictionary with detailed point information.

    Returns:
        Total points earned by the inputed golfer for the inputed week.

        If no scores found for golfer for this week, returns "No scores found for golfer for this week".
        If no matchups found for this week, returns "No matchups found for this week".
        If no opponent team found for the given matchup, returns "No opponent team found for the given matchup".

    """

    detail = kwargs.get('detail', False)

    # Get all scores for the inputed week and golfer
    scores = Score.objects.filter(golfer=golfer_model, week=week_model)

    # Check if there are any scores for the week and golfer
    if not scores:
        return "No scores found for golfer for this week"

    # Check if there are any matchups for the week
    matchups = week_model.matchup_set.all()
    if not matchups:
        return "No matchups found for this week"

    # Get the golfers on the same team as the inputed golfer
    golfer_team = golfer_model.team_set.first()
    team_golfers = golfer_team.golfers.all()

    # Get golfers partner
    for golfer in team_golfers:
        if golfer != golfer_model:
            partner = golfer

    # Try to get opponents team and return messege if not found
    for matchup in matchups:
        opponent_team = matchup.teams.exclude(id=golfer_team.id).first()
        if not opponent_team:
            return "No opponent team found for the given matchup"

    # Get opponent teams golfers
    opponent_golfers = opponent_team.golfers.all()

    golfer_hcp = getHcp(golfer_model, week_model)
    partner_hcp = getHcp(partner, week_model)
    opp_golfer1_hcp = getHcp(opponent_golfers[0], week_model)
    opp_golfer2_hcp = getHcp(opponent_golfers[1], week_model)

    if golfer_hcp > partner_hcp:
        if opp_golfer1_hcp > opp_golfer2_hcp:
            opponent = opponent_golfers[0]
            opponent_hcp = opp_golfer1_hcp
        else:
            opponent = opponent_golfers[1]
            opponent_hcp = opp_golfer2_hcp
    else:
        if opp_golfer1_hcp < opp_golfer2_hcp:
            opponent = opponent_golfers[0]
            opponent_hcp = opp_golfer1_hcp
        else:
            opponent = opponent_golfers[1]
            opponent_hcp = opp_golfer2_hcp

    opp_scores = Score.objects.filter(golfer=opponent, week=week_model)

    # Initialize the points to 0
    points = 0
    opponents_points = 0

    if week_model.is_front:
        holes = range(1, 10)
    else:
        holes = range(10, 19)


    hole_data = []
    opponents_hole_data = []

    # Iterate over the holes and calculate the points for each golfer
    for hole in holes:

        hole_point_data = {}
        opponents_hole_point_data = {}

        # Get the net scores for the inputed golfer and their opponent
        golfer_score = scores.get(hole__number=hole).score
        opponent_score = opp_scores.get(hole__number=hole).score

        hole_point_data['score'] = golfer_score
        opponents_hole_point_data['score'] = opponent_score

        hole_point_data['hole'] = hole
        opponents_hole_point_data['hole'] = hole

        if golfer_hcp > opponent_hcp:
            hcp_diff = golfer_hcp - opponent_hcp
            getting = True
            giving = False
        elif golfer_hcp < opponent_hcp:
            hcp_diff =  opponent_hcp - golfer_hcp
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

        # apply handicaps
        if scores.get(hole__number=hole).hole.handicap9 <= hcp_diff:
            if giving:
                opponent_score = opponent_score - (1 + rollover)
                hole_point_data['handicap'] = 1 + rollover
                opponents_hole_point_data['handicap'] = -(1 + rollover)
            if getting:
                golfer_score = golfer_score - (1 + rollover)
                hole_point_data['handicap'] = -(1 + rollover)
                opponents_hole_point_data['handicap'] = 1 + rollover
        elif rollover == 1:
            if giving:
                opponent_score = opponent_score - 1
                hole_point_data['handicap'] = 1
                opponents_hole_point_data['handicap'] = -1
            if getting:
                golfer_score = golfer_score - 1
                hole_point_data['handicap'] = -1
                opponents_hole_point_data['handicap'] = 1

        # Calculate the points for the hole based on the net scores

        if golfer_score < opponent_score:
            points += 1
            hole_point_data['points'] = 1
            opponents_hole_point_data['points'] = 0
        elif golfer_score == opponent_score:
            points += 0.5
            opponents_points += 0.5
            hole_point_data['points'] = 0.5
            opponents_hole_point_data['points'] = 0.5
        else:
            opponents_points += 1
            hole_point_data['points'] = 0
            opponents_hole_point_data['points'] = 1

        hole_data.append(hole_point_data)
        opponents_hole_data.append(opponents_hole_point_data)

    # check round points
    round_score = 0
    for score in scores:
        round_score = round_score + score.score
    opp_round_score = 0

    for score in opp_scores:
        opp_round_score = opp_round_score + score.score

    round_score = round_score - golfer_hcp
    opp_round_score = opp_round_score - opponent_hcp

    # Calculate the points for the 9th hole based on the net scores
    if round_score < opp_round_score:
        points += 3
        round_points = 3
        opponents_round_points = 0
    elif round_score == opp_round_score:
        points += 1.5
        round_points = 1.5
        opponents_points += 1.5
        opponents_round_points = 1.5
    else:
        opponents_points += 3
        opponents_round_points = 3
        round_points = 0

    if detail:
        return {'golfer': golfer_model, 'golfer_points': points, 'opponent': opponent, 'opponent_points': opponents_points, 'hole_data': hole_data, 'opponents_hole_data': opponents_hole_data, 'round_points': round_points, 'opponents_round_points': opponents_round_points}
    else:
        return points
