from main.models import *
from .week_management import get_current_season


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


def get_sub(golfer, week):
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
        if Sub.objects.get(absent_golfer=golfer, week=week).no_sub:
            return None
        else:
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