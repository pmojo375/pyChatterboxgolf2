from main.models import *
from .golfer_management import golfer_played


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