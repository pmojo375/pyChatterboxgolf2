from django.core.management.base import BaseCommand
from main.models import Season, Round, GolferMatchup
from main.helper import process_season


class Command(BaseCommand):
    help = 'Process a season by generating handicaps, golfer matchups, and rounds'

    def add_arguments(self, parser):
        parser.add_argument(
            'year',
            type=int,
            help='The year of the season to process'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force processing even if data already exists'
        )

    def handle(self, *args, **options):
        year = options['year']
        force = options['force']
        
        try:
            season = Season.objects.get(year=year)
        except Season.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Season for year {year} does not exist.')
            )
            return
        
        self.stdout.write(f'Processing season {year}...')
        
        if not force:
            # Check if data already exists by going through Week model
            existing_rounds = Round.objects.filter(week__season=season).count()
            existing_matchups = GolferMatchup.objects.filter(week__season=season).count()
            
            if existing_rounds > 0 or existing_matchups > 0:
                self.stdout.write(
                    self.style.WARNING(
                        f'Season {year} already has data: {existing_rounds} rounds, {existing_matchups} matchups. '
                        f'Use --force to process anyway.'
                    )
                )
                return
        
        # Process the season
        result = process_season(season)
        
        if result['status'] == 'success':
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully processed season {year}!\n'
                    f'  - Handicaps: {result["handicaps_generated"]}\n'
                    f'  - Matchups: {result["matchups_generated"]}\n'
                    f'  - Rounds: {result["rounds_generated"]}\n'
                    f'  - Weeks: {result["weeks_processed"]}'
                )
            )
        elif result['status'] == 'no_scores':
            self.stdout.write(
                self.style.WARNING(f'Season {year} has no scores to process.')
            )
        else:
            self.stdout.write(
                self.style.ERROR(f'Error processing season {year}.')
            ) 