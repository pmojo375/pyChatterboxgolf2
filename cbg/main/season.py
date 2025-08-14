from main.models import Week, Team, Matchup
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

        # Gather future weeks in chronological order
        future_weeks = list(
            Week.objects.filter(season=week.season, date__gt=week.date).order_by('date')
        )

        # Create a new final week (to keep count), alternating the side
        last_week_before_append = Week.objects.filter(season=week.season).order_by('-date').first()
        new_week = Week(
            season=week.season,
            number=last_week_before_append.number + 1,
            date=last_week_before_append.date + timedelta(weeks=1),
            is_front=not last_week_before_append.is_front,
            rained_out=False,
        )
        new_week.save()

        # Shift matchups forward so original week numbers retain their matchups
        shift_sources = [week] + future_weeks
        shift_targets = future_weeks + [new_week]
        for src_week, dst_week in zip(shift_sources, shift_targets):
            for mu in list(Matchup.objects.filter(week=src_week)):
                mu.week = dst_week
                mu.save()

        # Compress numbers of future weeks by one (keep front/back as-is)
        for future_week in future_weeks:
            future_week.number = future_week.number - 1
            future_week.save()
    else:
        week.rained_out = False
        week.save()

        # Gather future weeks in chronological order
        future_weeks = list(
            Week.objects.filter(season=week.season, date__gt=week.date).order_by('date')
        )

        # Identify final week to remove
        last_week_to_delete = Week.objects.filter(season=week.season).order_by('-date').first()

        # Shift matchups backward to restore original week alignments
        shift_chain = [week] + future_weeks + [last_week_to_delete]
        for i in range(len(shift_chain) - 1, 0, -1):
            src_week = shift_chain[i]
            dst_week = shift_chain[i - 1]
            for mu in list(Matchup.objects.filter(week=src_week)):
                mu.week = dst_week
                mu.save()

        # Expand numbers of future weeks by one
        for future_week in future_weeks:
            future_week.number = future_week.number + 1
            future_week.save()

        # Remove the final week
        last_week_to_delete.delete()

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