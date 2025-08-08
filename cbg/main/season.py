from main.models import Week, Team
from datetime import timedelta


def create_weeks(season, weeks, start_date):
    """
    Create a specified number of weeks for a given season, starting from a specified date.

    Args:
        season (Season): The season object for which the weeks are being created.
        weeks (int): The number of weeks to create.
        start_date (datetime): The starting date for the weeks (should be timezone-aware).

    Returns:
        int: The total number of weeks created.
    """
    # Assume start_date is timezone-aware
    for i in range(1, weeks + 1):
        week_date = start_date + timedelta(weeks=i-1)
        is_front = (i % 2 != 0)
        week = Week(season=season, number=i, date=week_date, is_front=is_front, rained_out=False)
        week.save()
    return weeks

def rain_out_update(week):
    """
    Update the rained_out field for a given week and the future weeks front/back status and dates.

    Args:
        week (Week): The week object to update.
    """
    
    if week.rained_out == False:
        week.rained_out = True
        
        week.save()
        
        # get future weeks ordered by date with the first week being the week after the current week
        future_weeks = Week.objects.filter(season=week.season, date__gt=week.date).order_by('date')
        
        # update the front/back status and date for each future week
        for future_week in future_weeks:
            future_week.is_front = not future_week.is_front
            future_week.number = future_week.number - 1
            future_week.save()
            
        # get the last week in the season
        last_week = Week.objects.filter(season=week.season).order_by('-date').first()
        new_week = Week(season=week.season, number=last_week.number + 1, date=last_week.date + timedelta(weeks=1), is_front=not last_week.is_front, rained_out=False)
        new_week.save()
    else:
        week.rained_out = False
        week.save()
        
        # get future weeks ordered by date with the first week being the week after the current week
        future_weeks = Week.objects.filter(season=week.season, date__gt=week.date).order_by('date')
        
        # update the front/back status and date for each future week
        for future_week in future_weeks:
            future_week.is_front = not future_week.is_front
            future_week.number = future_week.number + 1
            future_week.save()
        
        # get the last week in the season
        last_week = Week.objects.filter(season=week.season).order_by('-date').first()
        
        # delete the last week in the season
        last_week.delete()

def create_teams(season, golfers):
    """
    Create teams for a given season with a list of golfers.

    Args:
        season (Season): The season object for which the teams are being created.
        golfers (list): A list of golfer objects to create teams with.

    Returns:
        int: The status of the team creation. 1 if successful, 0 if not.

    """
    
    if len(golfers) == 2 and not Team.objects.filter(season=season, golfers__in=golfers).exists() and golfers[0] != golfers[1]:
        team = Team(season=season)
        team.save()
        team.golfers.add(*golfers)
        return 1
    else:
        return 0