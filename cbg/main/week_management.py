from datetime import timedelta
from main.models import *
from django.utils import timezone


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
            if Score.objects.filter(week=week).exists():
                return week
            
        return None


def get_next_week():
    print('Getting next week')
    current_season = get_current_season()
    if not current_season:
        return None
    # Get all weeks in order (by number or date)
    weeks = Week.objects.filter(season=current_season).order_by('number')
    for week in weeks:
        if not week.rained_out:
            score_count = Score.objects.filter(week=week).count()
            if score_count == 0:
                return week
    return None


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