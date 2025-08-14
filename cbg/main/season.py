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
    Mark a week as rained out (or undo), shift subsequent week numbers, and maintain
    the calendar's front/back rotation based on dates.

    - When marking as rained out: compress subsequent weeks by one number (no side flip),
      then append a new week at the end with the alternating side.
    - When un-marking: expand subsequent weeks by one number (no side flip),
      then remove the final week to restore the original count.

    This ensures that if week X was Front and gets rained out, the new week X (the
    next calendar week) will be Back, since its side was already scheduled that way.
    """

    if week.rained_out is False:
        week.rained_out = True
        week.save()

        # Pull future weeks forward by one number, keep their front/back as scheduled
        future_weeks = Week.objects.filter(
            season=week.season, date__gt=week.date
        ).order_by('date')

        for future_week in future_weeks:
            future_week.number = future_week.number - 1
            future_week.save()

        # Append a new week at the end, alternating the front/back
        last_week = Week.objects.filter(season=week.season).order_by('-date').first()
        new_week = Week(
            season=week.season,
            number=last_week.number + 1,
            date=last_week.date + timedelta(weeks=1),
            is_front=not last_week.is_front,
            rained_out=False,
        )
        new_week.save()
    else:
        week.rained_out = False
        week.save()

        # Push future weeks back by one number, keep their front/back as scheduled
        future_weeks = Week.objects.filter(
            season=week.season, date__gt=week.date
        ).order_by('date')

        for future_week in future_weeks:
            future_week.number = future_week.number + 1
            future_week.save()

        # Remove the final week to restore schedule length
        last_week = Week.objects.filter(season=week.season).order_by('-date').first()
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