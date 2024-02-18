from datetime import datetime
from main.models import *

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

    if Sub.objects.filter(absent_golfer=golfer, week=week).exists():
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
        if num_weeks < 5:
            # If there are fewer than 5 weeks, use all the scores and subtract 36 (par) from each score
            handicap = (sum(score for scores in scores_by_week.values() for score in scores) / num_weeks - 36) * 0.8
        else:
            # If there are 5 or more weeks, drop the highest- and lowest-scoring weeks and use the remaining scores
            drop_weeks = [weeks[0], weeks[-1]]
            scores = [score for week in weeks if week not in drop_weeks for score in scores_by_week[week]]
            handicap = (sum(scores) / (num_weeks - len(drop_weeks)) - 36) * 0.8

        return round(handicap, 5)
    else:
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
                golfer_points = get_golfer_points(week, golfer)
                if isinstance(golfer_points, (int, float)):  # Only add points if the function returns a number
                    total_points += golfer_points

        # Store the team points in the dictionary
        team_points[team.id] = total_points

    return team_points


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
    
    weeks_subs = Sub.objects.filter(week=week_model)
    
    subs = []
    
    # Get all subs for the inputed week
    for sub in weeks_subs:
        subs.append(sub.sub_golfer)

    detail = kwargs.get('detail', False)


    # Get the golfers on the same team as the inputed golfer
    try:
        golfer_team = golfer_model.team_set.get(season=week_model.season)
    except Team.DoesNotExist:
        golfer_team = get_absent_team_from_sub(golfer_model, week_model)
        
    # Gets the teams golfers. If the golfer is a sub, the team will be the absent team.
    team_golfers = golfer_team.golfers.all()

    if golfer_model in subs:
        absent_golfer = weeks_subs.get(sub_golfer=golfer_model).absent_golfer
    else:
        absent_golfer = golfer_model
        
    # Get golfers partner this will not work if the golfer is a sub need to fix.
    for golfer in team_golfers:
        if golfer != absent_golfer:
            partner = golfer
    
    # Get the matchup for the inputed week and golfer's team
    matchup = Matchup.objects.get(week=week_model, teams=golfer_team)
    
    # Get both teams from the matchup
    teams = matchup.teams.all()

    # Get the opponents team
    opponent_team = teams.exclude(id=golfer_team.id).first()

    # Get opponent teams golfers
    opponent_golfers = opponent_team.golfers.all()
    
    # Get subs if any were needed for the 4 golfers in the matchup
    golfer_model = get_sub(golfer_model, week_model)
    partner = get_sub(partner, week_model)
    opponent_golfers1 = get_sub(opponent_golfers[0], week_model)
    opponent_golfers2 = get_sub(opponent_golfers[1], week_model)
    
    # Get all scores for the inputed week and golfer
    scores = Score.objects.filter(golfer=golfer_model, week=week_model)
    
    golfer_hcp = get_hcp(golfer_model, week_model)
    partner_hcp = get_hcp(partner, week_model)
    opp_golfer1_hcp = get_hcp(opponent_golfers1, week_model)
    opp_golfer2_hcp = get_hcp(opponent_golfers2, week_model)


    # BUG: if the two golfers have the same handicap they both play the same opponent. This is not correct.
    if golfer_hcp >= partner_hcp:
        if opp_golfer1_hcp >= opp_golfer2_hcp:
            opponent = opponent_golfers1
            opponent_hcp = opp_golfer1_hcp
        else:
            opponent = opponent_golfers2
            opponent_hcp = opp_golfer2_hcp
    else:
        if opp_golfer1_hcp < opp_golfer2_hcp:
            opponent = opponent_golfers1
            opponent_hcp = opp_golfer1_hcp
        else:
            opponent = opponent_golfers2
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
            
        hole_point_data['handicap'] = 0
        opponents_hole_point_data['handicap'] = 0
        
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
        
            
def calculate_and_save_handicaps_for_season(season, test_mode=False):
    # Get all the golfers who played in the season
    golfers = Golfer.objects.filter(score__week__season=season).distinct()

    # Get all the weeks in the season
    weeks = season.week_set.all()

    # Loop through each golfer and each week in the season
    for golfer in golfers:
        weeks_played = 0
        weeks_played_obj = []
        for week in weeks:
            # Calculate the golfer's handicap for the week
            handicap = calculate_handicap(golfer, season, week)
            
            if golfer_played(golfer, week):
                weeks_played_obj.append(week)
                weeks_played += 1

            if test_mode:
                try:
                    existing_handicap = Handicap.objects.get(golfer=golfer, week=week)
                    if existing_handicap.handicap != handicap and week.number > 3 and week.number < 20:
                        print(f"Handicap for golfer {golfer.name} in week {week.number} of {existing_handicap.handicap} does not match calculated value of {handicap}.")
                except Handicap.DoesNotExist:
                    if week.number > 3 and week.number < 20:
                        print(f"No existing handicap for golfer {golfer.name} in week {week.number}. New handicap will be {handicap}.")
            else:
                # Save the calculated handicap in the database if it doesn't exist
                handicap_obj, created = Handicap.objects.get_or_create(golfer=golfer, week=week, defaults={'handicap': handicap})

                # Update the handicap if it already exists but has a different value
                if not created and handicap_obj.handicap != handicap:
                    handicap_obj.handicap = handicap
                    handicap_obj.save()

            # Update the first three weeks with the handicap calculated using the fourth week
            if weeks_played == 4 and not test_mode:
                first_three_weeks = weeks_played_obj[:3]
                for prev_week in first_three_weeks:
                    try:
                        handicap_obj = Handicap.objects.get(golfer=golfer, week=prev_week)
                        handicap_obj.handicap = handicap
                        handicap_obj.save()
                    except Handicap.DoesNotExist:
                        Handicap.objects.create(golfer=golfer, week=prev_week, handicap=handicap)   
        if weeks_played < 4 and not test_mode:
            # If golfer didnt play 4 weeks yet, apply the handicap of their last round to the first 3 or less weeks of the season
            most_recent_handicap = Handicap.objects.filter(golfer=golfer).order_by('-week__date').first()
            for week in weeks_played_obj:
                try:
                    handicap_obj = Handicap.objects.get(golfer=golfer, week=week)
                    handicap_obj.handicap = most_recent_handicap.handicap
                    handicap_obj.save()
                except Handicap.DoesNotExist:
                    Handicap.objects.create(golfer=golfer, week=week, handicap=most_recent_handicap.handicap)
            
    if test_mode:
        print("Test mode complete. No data was written to the database.")

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