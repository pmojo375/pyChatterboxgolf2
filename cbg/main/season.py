from main.models import Season, Week
from django.utils import timezone


def create_weeks(season, weeks, start_date):
    """
    Create a specified number of weeks for a given season, starting from a specified date.

    Args:
        season (Season): The season object for which the weeks are being created.
        weeks (int): The number of weeks to create.
        start_date (datetime): The starting date for the weeks.

    Returns:
        int: The total number of weeks created.

    """
    
    for i in range(1, weeks + 1):
        if i % 2 == 0:
            week = Week(season=season, number=i, date=start_date + timezone.timedelta(weeks=i-1), is_front=False, rained_out=False)
        else:
            week = Week(season=season, number=i, date=start_date + timezone.timedelta(weeks=i-1), is_front=True, rained_out=False)
        week.save()
        
    return weeks