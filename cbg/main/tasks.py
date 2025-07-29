from celery import shared_task
from main.models import GolferMatchup, Score, Golfer, Matchup, Week, Season, Team, Sub
from main.helper import get_sub, generate_golfer_matchups, process_week, calculate_and_save_handicaps_for_season, generate_rounds, generate_round
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
def recalculate_all_async(season_year):
    """Recalculate all data for a season: handicaps, matchups, and rounds"""
    try:
        season = Season.objects.get(year=season_year)
        
        # Step 1: Calculate handicaps for all weeks
        logger.info(f"Starting handicap calculation for season {season.year}")
        calculate_and_save_handicaps_for_season(season)
        
        # Step 2: Generate matchups for weeks that have team matchups entered
        teams = Team.objects.filter(season=season)
        total_teams = teams.count()
        expected_matchups = total_teams // 2
        
        matchup_weeks = []
        for week in Week.objects.filter(season=season, rained_out=False).order_by('number'):
            actual_matchups = Matchup.objects.filter(week=week).count()
            if actual_matchups == expected_matchups:
                generate_golfer_matchups(week)
                matchup_weeks.append(week.number)
                logger.info(f"Matchups generated for week {week.number}")
        
        # Step 3: Generate rounds for weeks with all scores entered
        round_weeks = []
        for week in Week.objects.filter(season=season, rained_out=False).order_by('number'):
            golfer_matchups = GolferMatchup.objects.filter(week=week)
            if golfer_matchups.exists():
                # Check if all scores are entered for this week
                no_sub_golfer_count = Sub.objects.filter(week=week, no_sub=True).count()
                expected_scores = ((total_teams * 2) - no_sub_golfer_count) * 9
                actual_scores = Score.objects.filter(week=week).count()
                
                if actual_scores == expected_scores:
                    # Generate rounds for each golfer matchup
                    for golfer_matchup in golfer_matchups:
                        generate_round(golfer_matchup)
                    round_weeks.append(week.number)
                    logger.info(f"Rounds generated for week {week.number} (all scores entered)")
                else:
                    logger.info(f"Skipping week {week.number} - only {actual_scores}/{expected_scores} scores entered")
        
        logger.info(f"Recalculation complete for season {season.year}")
        logger.info(f"Handicaps calculated for all weeks")
        logger.info(f"Matchups generated for {len(matchup_weeks)} weeks: {matchup_weeks}")
        logger.info(f"Rounds generated for {len(round_weeks)} weeks: {round_weeks}")
        
        return f"Recalculation complete for season {season.year}. Handicaps: all weeks, Matchups: {len(matchup_weeks)} weeks, Rounds: {len(round_weeks)} weeks"
        
    except Season.DoesNotExist:
        logger.error(f"Season with year {season_year} does not exist")
        return f"Season with year {season_year} does not exist"
    except Exception as e:
        logger.error(f"Error in recalculation for season {season_year}: {str(e)}")
        return f"Error in recalculation for season {season_year}: {str(e)}"



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
