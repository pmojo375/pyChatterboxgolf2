from main.models import *
from django.db.models import Sum
from .handicap_management import get_hcp
from .utils import conventional_round


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


def get_standings(season, week):
    """
    Get the standings for a given season and week.

    Args:
        season (Season): The season for which to get the standings.
        week (Week): The week for which to get the standings.

    Returns:
        List[Tuple[str
    """
    pass


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