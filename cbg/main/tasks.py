from celery import shared_task
from main.models import GolferMatchup, Score, Golfer, Matchup, Week, Season
from main.helper import get_sub, generate_golfer_matchups, process_week, calculate_and_save_handicaps_for_season, generate_rounds
import logging

logger = logging.getLogger(__name__)

@shared_task
def test_task():
    """Simple test task to verify Celery is working"""
    logger.info("Test task executed successfully!")
    return "Test task completed successfully!"

@shared_task
def process_week_async(week_id):
    """Process a week asynchronously"""
    try:
        week = Week.objects.get(id=week_id)
        process_week(week)
        logger.info(f"Week {week.number} processed successfully")
        return f"Week {week.number} processed successfully"
    except Week.DoesNotExist:
        logger.error(f"Week with id {week_id} does not exist")
        return f"Week with id {week_id} does not exist"
    except Exception as e:
        logger.error(f"Error processing week {week_id}: {str(e)}")
        return f"Error processing week {week_id}: {str(e)}"

@shared_task
def generate_matchups_async(week_id):
    """Generate golfer matchups for a week asynchronously"""
    try:
        week = Week.objects.get(id=week_id)
        generate_golfer_matchups(week)
        logger.info(f"Matchups generated for week {week.number}")
        return f"Matchups generated for week {week.number}"
    except Week.DoesNotExist:
        logger.error(f"Week with id {week_id} does not exist")
        return f"Week with id {week_id} does not exist"
    except Exception as e:
        logger.error(f"Error generating matchups for week {week_id}: {str(e)}")
        return f"Error generating matchups for week {week_id}: {str(e)}"



@shared_task
def calculate_handicaps_async(season_year, weeks=None, golfers=None):
    """Calculate and save handicaps for a season asynchronously"""
    try:
        season = Season.objects.get(year=season_year)
        calculate_and_save_handicaps_for_season(season, weeks=weeks, golfers=golfers)
        logger.info(f"Handicaps calculated for season {season.year}")
        return f"Handicaps calculated for season {season.year}"
    except Season.DoesNotExist:
        logger.error(f"Season with year {season_year} does not exist")
        return f"Season with year {season_year} does not exist"
    except Exception as e:
        logger.error(f"Error calculating handicaps for season {season_year}: {str(e)}")
        return f"Error calculating handicaps for season {season_year}: {str(e)}"

@shared_task
def generate_rounds_async(season_year):
    """Generate rounds for a season asynchronously"""
    try:
        season = Season.objects.get(year=season_year)
        generate_rounds(season)
        logger.info(f"Rounds generated for season {season.year}")
        return f"Rounds generated for season {season.year}"
    except Season.DoesNotExist:
        logger.error(f"Season with year {season_year} does not exist")
        return f"Season with year {season_year} does not exist"
    except Exception as e:
        logger.error(f"Error generating rounds for season {season_year}: {str(e)}")
        return f"Error generating rounds for season {season_year}: {str(e)}"
