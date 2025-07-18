from main.models import *
from django.db.models import Sum
from .golfer_management import golfer_played
from .handicap_management import get_hcp
from .points_management import get_golfer_points
from .utils import conventional_round


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
    from .handicap_management import calculate_and_save_handicaps_for_season
    calculate_and_save_handicaps_for_season(week.season)

    generate_golfer_matchups(week)
    
    # get the golfer matchups for the week
    golfer_matchups = GolferMatchup.objects.filter(week=week)

    for golfer_matchup in golfer_matchups:
        generate_round(golfer_matchup)