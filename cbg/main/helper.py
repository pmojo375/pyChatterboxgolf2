from main.models import *
from django.db.models import Sum, Count, Q
from django.utils import timezone
import random
import math


# Handicap rulesets (hardcoded defaults; structure-ready for future model-driven rules)
DEFAULT_MEMBER_HCP_RULES = {
    'max_weeks': 10,            # cap qualifying rounds considered
    'required_holes': 9,        # must have at least this many holes to count
    'establish_after_n_weeks': 3,  # include current until establishment; then prior-only
    'drop_best': 1,             # number of best (lowest delta) rounds to drop when eligible
    'drop_worst': 1,            # number of worst (highest delta) rounds to drop when eligible
    'drop_start_threshold': 5,  # start dropping only when at least this many rounds exist
    'adjust_factor': 0.8,       # 80% factor
    'rounding_precision': 5,    # decimals to round final handicap
}

DEFAULT_SUB_HCP_RULES = {
    'max_weeks': 10,
    'required_holes': 9,
    'establish_after_n_weeks': 1,  # subs establish after first round
    'drop_best': 0,
    'drop_worst': 0,
    'drop_start_threshold': 0,
    'adjust_factor': 0.8,
    'rounding_precision': 5,
}

def conventional_round(value):
    """
    Conventional rounding: 0.5 and up round up, under 0.5 round down.
    This is different from Python's built-in round() which uses banker's rounding.
    """
    return math.floor(value + 0.5)


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


def get_current_season(year=None):
    """Gets the season object for a specific year or the most recent season if no year is specified

    Parameters
    ----------
    year : int, optional
        The year to get the season for. If None, returns the most recent season.

    Returns
    -------
    Season
        The season object for the specified year or the most recent season, or None if no season exists
    """

    if year is not None:
        # Get season for specific year
        if Season.objects.filter(year=year).exists():
            return Season.objects.get(year=year)
        else:
            return None
    else:
        # Get the most recent season
        if Season.objects.exists():
            return Season.objects.all().order_by('-year')[0]
        else:
            return None


def get_last_week(season=None):

    print('Getting last week')
    # check if season exists
    if season is None:
        season = get_current_season()
    
    if not season: 
        return None
    else:
        # get the latest week that was played before the current date
        weeks = Week.objects.filter(season=season, date__lt=timezone.now()).order_by('-date')
        
        for week in weeks:
            score_count = Score.objects.filter(week=week).count()
            # For historical seasons, be more flexible - if there are scores, consider it played
            # For current season, be more strict about having all expected scores
            if score_count > 0:
                # If it's the current season, check for complete scores
                current_season = get_current_season()
                if season == current_season and score_count < week.num_scores:
                    continue
                return week
            
        return None


def get_next_week(season=None):
    print('Getting next week')
    if season is None:
        season = get_current_season()
    if not season:
        return None
    # Get all weeks in order (by number) starting from week 1
    weeks = Week.objects.filter(season=season).order_by('number')
    for week in weeks:
        if not week.rained_out:
            score_count = Score.objects.filter(week=week).count()
            # Find first week with 0 scores or fewer scores than expected
            if score_count == 0 or score_count < week.num_scores:
                print(f'Found next week: {week.number} (scores: {score_count}/{week.num_scores})')
                return week
    return None


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
        # Get points objects AFTER calculating points - filter by opponent to get correct Points for this matchup
        opponent = golfer_matchup.opponent
        points_objs = Points.objects.filter(golfer=golfer, week=week, opponent=opponent).order_by('hole__number')
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
                match_low = [(team1_golfer2.name, team1_golfer2_hcp), (team2_golfer2.name, team2_golfer2_hcp)]
                match_high = [(team1_golfer1.name, team1_golfer1_hcp), (team2_golfer1.name, team2_golfer1_hcp)]
            elif team1_golfer1_hcp < team1_golfer2_hcp and team2_golfer1_hcp < team2_golfer2_hcp:
                match_low = [(team1_golfer1.name, team1_golfer1_hcp), (team2_golfer1.name, team2_golfer1_hcp)]
                match_high = [(team1_golfer2.name, team1_golfer2_hcp), (team2_golfer2.name, team2_golfer2_hcp)]
            elif team1_golfer1_hcp > team1_golfer2_hcp and team2_golfer1_hcp < team2_golfer2_hcp:
                match_low = [(team1_golfer2.name, team1_golfer2_hcp), (team2_golfer1.name, team2_golfer1_hcp)]
                match_high = [(team1_golfer1.name, team1_golfer1_hcp), (team2_golfer2.name, team2_golfer2_hcp)]
            else:
                match_low = [(team1_golfer1.name, team1_golfer1_hcp), (team2_golfer2.name, team2_golfer2_hcp)]
                match_high = [(team1_golfer2.name, team1_golfer2_hcp), (team2_golfer1.name, team2_golfer1_hcp)]

            schedule.append({'low_match': match_low, 'high_match': match_high})

        return schedule


def get_golfer_schedule(week_model):
    """
    Given a week model, return the schedule of team matchups with individual golfer details.
    
    This function returns team matchups but with individual golfer names, handicaps, and sub info
    in a format similar to the original team-based schedule.
    
    :param week_model: The week model to retrieve the schedule for.
    :type week_model: cbg.main.models.Week
    :return: The schedule of team matchups with golfer details for the given week.
    :rtype: List[Dict]
    """
    golfer_matchups = GolferMatchup.objects.filter(week=week_model).select_related(
        'golfer', 'opponent', 'subbing_for_golfer'
    ).order_by('is_A', 'golfer__name')
    
    if not golfer_matchups.exists():
        return None
    
    schedule = []
    team_matchups = week_model.matchup_set.all()
    
    for matchup in team_matchups:
        teams = list(matchup.teams.all())
        if len(teams) == 2:
            team1, team2 = teams[0], teams[1]
            
            team1_golfer_matchups = golfer_matchups.filter(
                Q(golfer__in=team1.golfers.all()) | Q(subbing_for_golfer__in=team1.golfers.all())
            )
            
            team2_golfer_matchups = golfer_matchups.filter(
                Q(golfer__in=team2.golfers.all()) | Q(subbing_for_golfer__in=team2.golfers.all())
            )
            
            # Prepare golfer details for each team with handicap sorting
            team1_golfers = []
            team2_golfers = []
            
            for gm in team1_golfer_matchups:
                golfer_name = gm.golfer.name
                if gm.subbing_for_golfer:
                    golfer_name += f" (sub for {gm.subbing_for_golfer.name})"
                
                golfer_hcp = gm.golfer.handicap_set.filter(week=week_model).first()
                golfer_hcp_value = golfer_hcp.handicap if golfer_hcp else 999  # High default for missing handicaps
                
                team1_golfers.append((golfer_name, golfer_hcp_value))
            
            for gm in team2_golfer_matchups:
                golfer_name = gm.golfer.name
                if gm.subbing_for_golfer:
                    golfer_name += f" (sub for {gm.subbing_for_golfer.name})"
                
                golfer_hcp = gm.golfer.handicap_set.filter(week=week_model).first()
                golfer_hcp_value = golfer_hcp.handicap if golfer_hcp else 999  # High default for missing handicaps
                
                team2_golfers.append((golfer_name, golfer_hcp_value))
            
            # Sort by handicap (lower handicap = A golfer, goes first)
            team1_golfers.sort(key=lambda x: x[1])
            team2_golfers.sort(key=lambda x: x[1])
            
            # Create the matchup entry in a format similar to original team schedule
            if team1_golfers and team2_golfers:
                # Golfers are now sorted by handicap (A = lower handicap, B = higher handicap)
                schedule.append({
                    'high_match': (team1_golfers[0] if len(team1_golfers) > 0 else ('', 0), 
                                 team2_golfers[0] if len(team2_golfers) > 0 else ('', 0)),
                    'low_match': (team1_golfers[1] if len(team1_golfers) > 1 else ('', 0), 
                                team2_golfers[1] if len(team2_golfers) > 1 else ('', 0)),
                    'is_golfer_schedule': True  # Flag to indicate this is golfer-based data
                })
    
    return schedule


def get_front_holes(season):
    """
    Retrieve the front holes for a given season's course config.
    NOTE: When using these holes for stats, always filter scores by week__season=season, not just by hole/config.
    """
    hole_numbers = range(1, 10)
    return Hole.objects.filter(config=season.course_config, number__in=hole_numbers).order_by('number')


def get_back_holes(season):
    """
    Retrieve the back holes for a given season's course config.
    NOTE: When using these holes for stats, always filter scores by week__season=season, not just by hole/config.
    """
    hole_numbers = range(10, 19)
    return Hole.objects.filter(config=season.course_config, number__in=hole_numbers).order_by('number')


def get_nine_par_totals(season):
    """
    Return total par for front and back nines for a season using Hole data.
    Falls back to 36 if par data is missing.
    """
    front_par_total = get_front_holes(season).aggregate(Sum('par'))['par__sum'] or 36
    back_par_total = get_back_holes(season).aggregate(Sum('par'))['par__sum'] or 36
    return {'front': front_par_total, 'back': back_par_total}


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
    
    # Check if this is a virtual matchup (opponent team has no subs)
    golfer_opponent_team_no_subs = golfer_matchup.opponent_team_no_subs
    
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
            Points.objects.update_or_create(
                golfer=golfer_model, 
                week=week_model, 
                hole=hole, 
                opponent=opponent,
                defaults={'score': golfer_score_model, 'points': 1}
            )
        elif golfer_score == opponent_score:
            points += 0.5
            # In virtual matchups, ties still give golfer 0.5 but opponent gets 0
            if golfer_opponent_team_no_subs:
                opp_points += 0  # Virtual opponent gets no points
            else:
                opp_points += 0.5
            Points.objects.update_or_create(
                golfer=golfer_model, 
                week=week_model, 
                hole=hole, 
                opponent=opponent,
                defaults={'score': golfer_score_model, 'points': 0.5}
            )
        else:
            # Golfer loses the hole
            if golfer_opponent_team_no_subs:
                opp_points += 0  # Virtual opponent cannot take points
            else:
                opp_points += 1
            Points.objects.update_or_create(
                golfer=golfer_model, 
                week=week_model, 
                hole=hole, 
                opponent=opponent,
                defaults={'score': golfer_score_model, 'points': 0}
            )
        

    
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
        # In virtual matchups, the opponent won't have a matchup record
        pass

    # Calculate the points for the 9th hole based on the net scores
    # Handle different scenarios for round points
    if golfer_opponent_team_no_subs:
        # Virtual matchup - golfer automatically gets 3 points for low net score
        # Opponent cannot take any points since they already have their own matchup
        points += 3
        round_points = 3
        opp_round_points = 0  # Virtual opponent gets no round points
    elif golfer_is_teammate_subbing and opponent_is_teammate_subbing:
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


def calculate_handicap(golfer, season, week, ruleset_member=None, ruleset_sub=None):
    """
    Calculate handicap using weekly totals and dynamic par, based on configurable rulesets.
    This function is stateless and prior-only: it considers only complete rounds strictly
    before the target week. Establishment/backfill behavior is handled by the season-level
    driver function, not here.
    """

    # Resolve rulesets (members vs subs)
    is_full_time_member = Golfer.objects.filter(id=golfer.id, team__season=season).exists()
    member_rules = ruleset_member or DEFAULT_MEMBER_HCP_RULES
    sub_rules = ruleset_sub or DEFAULT_SUB_HCP_RULES
    rules = member_rules if is_full_time_member else sub_rules

    # Build base queryset for prior weeks only (strictly before target week)
    base_filter = Q(golfer=golfer, week__season=season, week__date__lt=week.date)

    weekly_qs_all = (
        Score.objects
        .filter(base_filter)
        .values('week', 'week__is_front', 'week__date')
        .annotate(week_total=Sum('score'), num_holes=Count('id'))
        .order_by('-week__date')
    )

    if not weekly_qs_all.exists():
        return 0

    # Only consider complete prior weeks
    complete_weeks_all = [
        {
            'week_id': row['week'],
            'is_front': row['week__is_front'],
            'date': row['week__date'],
            'week_total': row['week_total'],
        }
        for row in weekly_qs_all if row['num_holes'] >= rules.get('required_holes', 9)
    ]

    if not complete_weeks_all:
        return 0

    # Use most recent up to max_weeks
    weeks_to_use_sorted = sorted(complete_weeks_all, key=lambda x: x['date'], reverse=True)
    weeks_to_use_limited = weeks_to_use_sorted[: rules.get('max_weeks', 10)]

    # Get dynamic par totals for the season (always on)
    par_totals = get_nine_par_totals(season)

    # Build weekly deltas (gross - par) per week
    weekly_deltas = []
    for row in weeks_to_use_limited:
        par_for_nine = par_totals['front'] if row['is_front'] else par_totals['back']
        weekly_deltas.append(row['week_total'] - par_for_nine)

    # Apply drop rule when applicable (full-time member and at least 5 weeks)
    drop_best = rules.get('drop_best', 0)
    drop_worst = rules.get('drop_worst', 0)
    drop_threshold = rules.get('drop_start_threshold', 0)

    if len(weekly_deltas) >= drop_threshold and (drop_best > 0 or drop_worst > 0):
        deltas_sorted = sorted(weekly_deltas)
        start = min(drop_best, len(deltas_sorted))
        end = len(deltas_sorted) - min(drop_worst, len(deltas_sorted) - start)
        deltas_kept = deltas_sorted[start:end] if start < end else []
        if deltas_kept:
            avg_delta = sum(deltas_kept) / len(deltas_kept)
        else:
            avg_delta = sum(weekly_deltas) / len(weekly_deltas)
    else:
        avg_delta = sum(weekly_deltas) / len(weekly_deltas)

    handicap_value = avg_delta * rules.get('adjust_factor', 0.8)
    return round(handicap_value, rules.get('rounding_precision', 5))


def calculate_and_save_handicaps_for_season(
    season,
    weeks=None,
    golfers=None,
    ruleset_member: dict | None = None,
    ruleset_sub: dict | None = None,
):
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
        member_rules = ruleset_member or DEFAULT_MEMBER_HCP_RULES
        sub_rules = ruleset_sub or DEFAULT_SUB_HCP_RULES
        is_member = Golfer.objects.filter(id=golfer.id, team__season=season).exists()
        rules = member_rules if is_member else sub_rules
        establish_after = rules.get('establish_after_n_weeks', 3)
        adjust_factor = rules.get('adjust_factor', 0.8)
        rounding_precision = rules.get('rounding_precision', 5)
        required_holes = rules.get('required_holes', 9)
        max_weeks = rules.get('max_weeks', 10)

        # Track played, complete weeks for pre-establishment seeding/backfill
        weeks_played = 0
        weeks_played_list = []

        # Preload par totals once
        par_totals = get_nine_par_totals(season)

        for week in weeks:
            # Calculate the golfer's handicap for the week using prior-only logic
            handicap_prior_only = calculate_handicap(
                golfer,
                season,
                week,
                ruleset_member=member_rules,
                ruleset_sub=sub_rules,
            )

            # Save or update the prior-only handicap for this week
            handicap_obj, created = Handicap.objects.get_or_create(
                golfer=golfer, week=week, defaults={'handicap': handicap_prior_only}
            )
            if not created and handicap_obj.handicap != handicap_prior_only:
                handicap_obj.handicap = handicap_prior_only
                handicap_obj.save()

            # If golfer played this week and it's a complete round, track it
            if golfer_played(golfer, week):
                hole_count = Score.objects.filter(golfer=golfer, week=week).count()
                if hole_count >= required_holes:
                    weeks_played_list.append(week)
                    weeks_played += 1

            # Pre-establishment behavior
            if weeks_played > 0 and weeks_played <= establish_after:
                # Compute seeded handicap from the played complete weeks including current
                # Use up to max_weeks most recent played weeks
                recent_weeks = sorted(weeks_played_list, key=lambda w: w.date, reverse=True)[:max_weeks]
                deltas = []
                for wk_used in recent_weeks:
                    total = Score.objects.filter(golfer=golfer, week=wk_used).aggregate(Sum('score'))['score__sum']
                    if total is None:
                        continue
                    par_for_nine = par_totals['front'] if wk_used.is_front else par_totals['back']
                    deltas.append(total - par_for_nine)
                if deltas:
                    seeded_hcp = round((sum(deltas) / len(deltas)) * adjust_factor, rounding_precision)
                    # Apply to all played weeks so far (retroactive backfill)
                    for wk_used in weeks_played_list:
                        prev_obj, _ = Handicap.objects.get_or_create(golfer=golfer, week=wk_used, defaults={'handicap': seeded_hcp})
                        if prev_obj.handicap != seeded_hcp:
                            prev_obj.handicap = seeded_hcp
                            prev_obj.save()

            # Post-establishment: do nothing special; prior-only applies to next week naturally


def generate_golfer_matchups(week):
    """
    Generates golfer matchups for a given week by pairing golfers from opposing teams
    and handling substitutions for absent golfers.
    This function performs the following steps:
    1. Retrieves all matchups for the specified week.
    2. Deletes any existing golfer matchups, rounds, and points for the week.
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

    # delete all rounds, golfer matchups, and points for the week to start fresh
    Round.objects.filter(week=week).delete()
    GolferMatchup.objects.filter(week=week).delete()
    Points.objects.filter(week=week).delete()

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

        # Check for teams where both golfers are absent with no_sub
        team1_both_absent_no_sub = (team1_golfer1_sub and team1_golfer1_sub.no_sub) and (team1_golfer2_sub and team1_golfer2_sub.no_sub)
        team2_both_absent_no_sub = (team2_golfer1_sub and team2_golfer1_sub.no_sub) and (team2_golfer2_sub and team2_golfer2_sub.no_sub)
        
        # Handle virtual matchups for teams that have no opponents
        if team1_both_absent_no_sub and not team2_both_absent_no_sub:
            # Team1 is completely absent, create virtual matchups for team2
            print(f'Team1 ({team1_original_golfer1.name} and {team1_original_golfer2.name}) both absent with no_sub, creating virtual matchups for team2')
            create_virtual_matchups_for_team(week, team2, team2_A_golfer, team2_B_golfer, team2_A_subbing_for, team2_B_subbing_for)
        elif team2_both_absent_no_sub and not team1_both_absent_no_sub:
            # Team2 is completely absent, create virtual matchups for team1
            print(f'Team2 ({team2_original_golfer1.name} and {team2_original_golfer2.name}) both absent with no_sub, creating virtual matchups for team1')
            create_virtual_matchups_for_team(week, team1, team1_A_golfer, team1_B_golfer, team1_A_subbing_for, team1_B_subbing_for)
        elif team1_both_absent_no_sub and team2_both_absent_no_sub:
            # Both teams completely absent - this shouldn't happen in normal circumstances
            print(f'Both teams completely absent with no_sub - no matchups created for this matchup')
        else:
            # Normal case - create regular golfer matchups
            GolferMatchup.objects.create(week=week, golfer=team1_A_golfer, is_A=True, opponent=team2_A_golfer, subbing_for_golfer=team1_A_subbing_for, is_teammate_subbing=team1_A_has_no_sub)
            GolferMatchup.objects.create(week=week, golfer=team2_A_golfer, is_A=True, opponent=team1_A_golfer, subbing_for_golfer=team2_A_subbing_for, is_teammate_subbing=team2_A_has_no_sub)
            GolferMatchup.objects.create(week=week, golfer=team1_B_golfer, is_A=False, opponent=team2_B_golfer, subbing_for_golfer=team1_B_subbing_for, is_teammate_subbing=team1_B_has_no_sub)
            GolferMatchup.objects.create(week=week, golfer=team2_B_golfer, is_A=False, opponent=team1_B_golfer, subbing_for_golfer=team2_B_subbing_for, is_teammate_subbing=team2_B_has_no_sub)
        
        # print subbing for golfers (only for normal matchups)
        if not (team1_both_absent_no_sub or team2_both_absent_no_sub):
            print(f'{team1_A_golfer.name} is subbing for {team1_A_subbing_for.name}') if team1_A_subbing_for else print(f'{team1_A_golfer.name} is not subbing')
            print(f'{team2_A_golfer.name} is subbing for {team2_A_subbing_for.name}') if team2_A_subbing_for else print(f'{team2_A_golfer.name} is not subbing')
            print(f'{team1_B_golfer.name} is subbing for {team1_B_subbing_for.name}') if team1_B_subbing_for else print(f'{team1_B_golfer.name} is not subbing')
            print(f'{team2_B_golfer.name} is subbing for {team2_B_subbing_for.name}') if team2_B_subbing_for else print(f'{team2_B_golfer.name} is not subbing')


def create_virtual_matchups_for_team(week, present_team, team_A_golfer, team_B_golfer, team_A_subbing_for, team_B_subbing_for):
    """
    Create virtual matchups for a team that has no opponents due to the opposing team having both golfers absent with no_sub.
    
    Args:
        week: The week object
        present_team: The team that is present and needs virtual opponents
        team_A_golfer: The A golfer from the present team
        team_B_golfer: The B golfer from the present team  
        team_A_subbing_for: Who the A golfer is subbing for (if anyone)
        team_B_subbing_for: Who the B golfer is subbing for (if anyone)
    """
    # Find the absent team (the team this present team was supposed to play against)
    matchup = Matchup.objects.get(week=week, teams=present_team)
    absent_team = matchup.teams.exclude(id=present_team.id).first()
    
    # Check if RandomDrawnTeam already exists for this absent team and week
    random_drawn_team_obj = RandomDrawnTeam.objects.filter(week=week, absent_team=absent_team).first()
    
    if random_drawn_team_obj:
        virtual_team = random_drawn_team_obj.drawn_team
        print(f'Using existing virtual team: {virtual_team} for absent team: {absent_team}')
    else:
        # Get all teams that actually played this week (have golfer matchups)
        playing_teams = Team.objects.filter(
            season=week.season,
            golfers__golfermatchup__week=week
        ).exclude(id=present_team.id).exclude(id=absent_team.id).distinct()
        
        if not playing_teams.exists():
            print(f'No teams available for virtual matchup for team {present_team}')
            return
            
        # Randomly select a team
        virtual_team = random.choice(list(playing_teams))
        
        # Create RandomDrawnTeam record
        random_drawn_team_obj = RandomDrawnTeam.objects.create(
            week=week,
            absent_team=absent_team,
            drawn_team=virtual_team
        )
        print(f'Created new virtual team assignment: {virtual_team} for absent team: {absent_team}')
    
    # Get the virtual opponents from the drawn team
    # We need to match A golfers with A golfers and B golfers with B golfers
    # Determine A/B status directly from handicaps since GolferMatchup objects might not exist yet
    virtual_team_golfers = list(virtual_team.golfers.all())
    
    if len(virtual_team_golfers) != 2:
        print(f'Virtual team {virtual_team} does not have exactly 2 golfers')
        return
    
    virtual_golfer1 = virtual_team_golfers[0]
    virtual_golfer2 = virtual_team_golfers[1]
    
    # Get handicaps to determine A/B status
    virtual_golfer1_hcp = get_hcp(virtual_golfer1, week)
    virtual_golfer2_hcp = get_hcp(virtual_golfer2, week)
    
    # Lower handicap golfer is A, higher handicap golfer is B
    if virtual_golfer1_hcp <= virtual_golfer2_hcp:
        virtual_A_golfer = virtual_golfer1
        virtual_B_golfer = virtual_golfer2
    else:
        virtual_A_golfer = virtual_golfer2
        virtual_B_golfer = virtual_golfer1
    
    # Create virtual golfer matchups for the present team
    # Note: We only create matchups for the present team, not the virtual opponents
    GolferMatchup.objects.create(
        week=week, 
        golfer=team_A_golfer, 
        is_A=True, 
        opponent=virtual_A_golfer, 
        subbing_for_golfer=team_A_subbing_for, 
        is_teammate_subbing=False,  # They're not subbing for teammates in this case
        opponent_team_no_subs=True
    )
    
    GolferMatchup.objects.create(
        week=week, 
        golfer=team_B_golfer, 
        is_A=False, 
        opponent=virtual_B_golfer, 
        subbing_for_golfer=team_B_subbing_for, 
        is_teammate_subbing=False,  # They're not subbing for teammates in this case
        opponent_team_no_subs=True
    )
    
    print(f'Created virtual matchups: {team_A_golfer.name} vs {virtual_A_golfer.name} (A), {team_B_golfer.name} vs {virtual_B_golfer.name} (B)')


def process_week(week):
    
    # generate the handicaps for the next week
    calculate_and_save_handicaps_for_season(week.season)

    # get all weeks before this week including this week
    weeks = Week.objects.filter(season=week.season, number__lte=week.number, rained_out=False)
    for week in weeks:
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
    Find the earliest week that doesn't have the expected number of matchups.
    Expected matchups are computed dynamically as (number of teams in the season) // 2.

    Args:
        season (Season, optional): The season to check. Defaults to current season.

    Returns:
        Week | None: The earliest week without the expected number of matchups, or None if all are full.
    """
    if season is None:
        season = get_current_season()

    if not season:
        return None

    # Determine expected number of matchups per week based on team count
    team_count = Team.objects.filter(season=season).count()
    expected_matchups = team_count // 2 if team_count > 0 else 0

    # Get all non-rained-out weeks for the season ordered by week number
    weeks = Week.objects.filter(season=season, rained_out=False).order_by('number')

    for week in weeks:
        matchup_count = Matchup.objects.filter(week=week).count()
        if matchup_count < expected_matchups:
            return week

    return None


def process_season(season):
    """
    Process an entire season by generating handicaps, golfer matchups, and rounds for all weeks.
    
    This function will:
    1. Calculate and save handicaps for all golfers in the season
    2. Generate golfer matchups for all weeks that have scores
    3. Generate rounds for all golfer matchups
    
    Args:
        season (Season): The season to process
        
    Returns:
        dict: A summary of what was processed including counts of handicaps, matchups, and rounds generated
    """
    print(f"Starting to process season {season.year}...")
    
    # Get all weeks in the season that have been played (have scores)
    weeks = Week.objects.filter(season=season).order_by('number')
    played_weeks = []
    
    for week in weeks:
        if Score.objects.filter(week=week).exists():
            played_weeks.append(week)
    
    print(f"Found {len(played_weeks)} weeks with scores out of {weeks.count()} total weeks")
    
    if not played_weeks:
        print("No weeks with scores found. Nothing to process.")
        return {
            'season': season.year,
            'handicaps_generated': 0,
            'matchups_generated': 0,
            'rounds_generated': 0,
            'weeks_processed': 0,
            'status': 'no_scores'
        }
    
    # Step 1: Calculate and save handicaps for the entire season
    print("Calculating handicaps...")
    calculate_and_save_handicaps_for_season(season)
    
    # Count handicaps generated
    handicaps_count = Handicap.objects.filter(week__season=season).count()
    print(f"Generated {handicaps_count} handicaps")
    
    # Step 2: Generate golfer matchups and rounds for each played week
    total_matchups = 0
    total_rounds = 0
    
    for week in played_weeks:
        print(f"Processing week {week.number}...")
        
        # Generate golfer matchups for this week
        generate_golfer_matchups(week)
        
        # Count matchups generated for this week
        week_matchups = GolferMatchup.objects.filter(week=week).count()
        total_matchups += week_matchups
        print(f"  Generated {week_matchups} golfer matchups")
        
        # Generate rounds for each matchup
        golfer_matchups = GolferMatchup.objects.filter(week=week)
        week_rounds = 0
        
        for golfer_matchup in golfer_matchups:
            try:
                generate_round(golfer_matchup)
                week_rounds += 1
            except Exception as e:
                print(f"  Error generating round for {golfer_matchup.golfer.name}: {e}")
        
        total_rounds += week_rounds
        print(f"  Generated {week_rounds} rounds")
    
    print(f"Season {season.year} processing complete!")
    print(f"Summary:")
    print(f"  - Handicaps generated: {handicaps_count}")
    print(f"  - Golfer matchups generated: {total_matchups}")
    print(f"  - Rounds generated: {total_rounds}")
    print(f"  - Weeks processed: {len(played_weeks)}")
    
    return {
        'season': season.year,
        'handicaps_generated': handicaps_count,
        'matchups_generated': total_matchups,
        'rounds_generated': total_rounds,
        'weeks_processed': len(played_weeks),
        'status': 'success'
    }
    
        
    