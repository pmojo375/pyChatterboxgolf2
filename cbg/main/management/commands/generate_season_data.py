from django.core.management.base import BaseCommand, CommandError
from django.db import transaction, models
from main.models import *
from main.helper import *
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Generate handicaps, golfer matchups, and rounds for a season'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--season',
            type=int,
            help='Season year to process (default: current season)'
        )
        parser.add_argument(
            '--week',
            type=int,
            help='Process only a specific week'
        )
        parser.add_argument(
            '--week-range',
            type=str,
            help='Process a range of weeks (e.g., "4-9" for weeks 4 through 9)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be generated without actually doing it'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force regeneration even if data already exists'
        )
        parser.add_argument(
            '--skip-handicaps',
            action='store_true',
            help='Skip handicap generation'
        )
        parser.add_argument(
            '--skip-matchups',
            action='store_true',
            help='Skip golfer matchup generation'
        )
        parser.add_argument(
            '--skip-rounds',
            action='store_true',
            help='Skip round generation'
        )

    def handle(self, *args, **options):
        season_year = options['season']
        specific_week = options['week']
        week_range = options['week_range']
        dry_run = options['dry_run']
        force = options['force']
        skip_handicaps = options['skip_handicaps']
        skip_matchups = options['skip_matchups']
        skip_rounds = options['skip_rounds']

        # Validate week range format if provided
        if week_range:
            try:
                start_week, end_week = map(int, week_range.split('-'))
                if start_week > end_week:
                    raise CommandError("Start week must be less than or equal to end week")
                if start_week < 1:
                    raise CommandError("Start week must be 1 or greater")
            except ValueError:
                raise CommandError("Week range must be in format 'start-end' (e.g., '4-9')")

        # Get the season
        if season_year:
            try:
                season = Season.objects.get(year=season_year)
            except Season.DoesNotExist:
                raise CommandError(f"Season {season_year} does not exist")
        else:
            season = get_current_season()
            if not season:
                raise CommandError("No current season found. Please specify a season year or create a current season.")

        self.stdout.write(f"Processing season: {season.year}")

        # Get weeks to process
        if specific_week:
            weeks = Week.objects.filter(season=season, number=specific_week)
            if not weeks.exists():
                raise CommandError(f"Week {specific_week} does not exist in season {season.year}")
        elif week_range:
            weeks = Week.objects.filter(season=season, number__range=[start_week, end_week]).order_by('number')
            if not weeks.exists():
                raise CommandError(f"No weeks found in range {start_week}-{end_week} for season {season.year}")
        else:
            # Get all weeks that have been played (have scores)
            weeks = Week.objects.filter(season=season).order_by('number')
            played_weeks = []
            for week in weeks:
                if Score.objects.filter(week=week).exists():
                    played_weeks.append(week)
            weeks = played_weeks

        if not weeks:
            self.stdout.write(self.style.WARNING("No weeks to process"))
            return

        self.stdout.write(f"Found {len(weeks)} weeks to process: {[w.number for w in weeks]}")

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made"))
            self.dry_run_generation(season, weeks, skip_handicaps, skip_matchups, skip_rounds)
        else:
            self.perform_generation(season, weeks, force, skip_handicaps, skip_matchups, skip_rounds)

    def dry_run_generation(self, season, weeks, skip_handicaps, skip_matchups, skip_rounds):
        """Show what would be generated without making changes"""
        
        if not skip_handicaps:
            # Count existing handicaps
            existing_handicaps = Handicap.objects.filter(week__season=season).count()
            self.stdout.write(f"Would generate handicaps for {len(weeks)} weeks (existing: {existing_handicaps})")

        if not skip_matchups:
            # Count existing matchups
            existing_matchups = GolferMatchup.objects.filter(week__season=season).count()
            self.stdout.write(f"Would generate golfer matchups for {len(weeks)} weeks (existing: {existing_matchups})")

        if not skip_rounds:
            # Count existing rounds
            existing_rounds = Round.objects.filter(week__season=season).count()
            self.stdout.write(f"Would generate rounds for {len(weeks)} weeks (existing: {existing_rounds})")

        # Show per-week breakdown
        self.stdout.write("\nPer-week breakdown:")
        for week in weeks:
            week_handicaps = Handicap.objects.filter(week=week).count()
            week_matchups = GolferMatchup.objects.filter(week=week).count()
            week_rounds = Round.objects.filter(week=week).count()
            week_scores = Score.objects.filter(week=week).count()
            
            status = "✓" if week_scores > 0 else "✗"
            self.stdout.write(f"  Week {week.number}: {status} {week_handicaps} handicaps, {week_matchups} matchups, {week_rounds} rounds, {week_scores} scores")

    def perform_generation(self, season, weeks, force, skip_handicaps, skip_matchups, skip_rounds):
        """Actually perform the generation"""
        
        with transaction.atomic():
            try:
                # Step 1: Generate handicaps for the season
                if not skip_handicaps:
                    self.stdout.write("Generating handicaps...")
                    calculate_and_save_handicaps_for_season(season, weeks=weeks)
                    handicap_count = Handicap.objects.filter(week__in=weeks).count()
                    self.stdout.write(self.style.SUCCESS(f"✓ Generated {handicap_count} handicaps"))

                # Step 2: Generate golfer matchups for each week
                if not skip_matchups:
                    self.stdout.write("Generating golfer matchups...")
                    total_matchups = 0
                    for week in weeks:
                        # Check if matchups exist for this week
                        existing_matchups = GolferMatchup.objects.filter(week=week).count()
                        if existing_matchups > 0 and not force:
                            self.stdout.write(f"  Week {week.number}: Skipping (already has {existing_matchups} matchups)")
                            continue
                        
                        # Delete existing matchups if force is enabled
                        if existing_matchups > 0 and force:
                            deleted_count = GolferMatchup.objects.filter(week=week).delete()[0]
                            self.stdout.write(f"  Week {week.number}: Deleted {deleted_count} existing matchups")
                        
                        # Generate new matchups
                        generate_golfer_matchups(week)
                        new_matchups = GolferMatchup.objects.filter(week=week).count()
                        total_matchups += new_matchups
                        self.stdout.write(f"  Week {week.number}: Generated {new_matchups} matchups")
                    
                    self.stdout.write(self.style.SUCCESS(f"✓ Generated {total_matchups} total golfer matchups"))

                # Step 3: Generate rounds for each week
                if not skip_rounds:
                    self.stdout.write("Generating rounds...")
                    total_rounds = 0
                    for week in weeks:
                        # Get golfer matchups for this week
                        golfer_matchups = GolferMatchup.objects.filter(week=week)
                        
                        if not golfer_matchups.exists():
                            self.stdout.write(f"  Week {week.number}: No golfer matchups found, skipping")
                            continue
                        
                        week_rounds = 0
                        for golfer_matchup in golfer_matchups:
                            # Check if round already exists
                            existing_round = Round.objects.filter(
                                golfer=golfer_matchup.golfer, 
                                week=week, 
                                golfer_matchup=golfer_matchup
                            ).first()
                            
                            if existing_round and not force:
                                continue
                            
                            # Delete existing round if force is enabled
                            if existing_round and force:
                                existing_round.delete()
                            
                            # Generate new round
                            try:
                                generate_round(golfer_matchup)
                                week_rounds += 1
                            except Exception as e:
                                self.stdout.write(self.style.ERROR(f"  Error generating round for {golfer_matchup.golfer.name} in week {week.number}: {e}"))
                        
                        total_rounds += week_rounds
                        self.stdout.write(f"  Week {week.number}: Generated {week_rounds} rounds")
                    
                    self.stdout.write(self.style.SUCCESS(f"✓ Generated {total_rounds} total rounds"))

                self.stdout.write(self.style.SUCCESS("✓ Season data generation completed successfully"))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error during generation: {e}"))
                raise

    def cleanup_duplicate_rounds(self, week):
        """Clean up any duplicate rounds that might have been created"""
        # Find rounds with the same golfer, week, and golfer_matchup
        duplicate_rounds = Round.objects.filter(week=week).values(
            'golfer', 'golfer_matchup'
        ).annotate(
            count=models.Count('id')
        ).filter(count__gt=1)
        
        for duplicate in duplicate_rounds:
            # Keep the first round, delete the rest
            rounds_to_delete = Round.objects.filter(
                golfer=duplicate['golfer'],
                week=week,
                golfer_matchup=duplicate['golfer_matchup']
            ).order_by('id')[1:]  # Skip the first one
            
            deleted_count = rounds_to_delete.delete()[0]
            if deleted_count > 0:
                self.stdout.write(f"  Cleaned up {deleted_count} duplicate rounds for {duplicate['golfer']}")

    def verify_data_integrity(self, season, weeks):
        """Verify that the generated data is consistent"""
        self.stdout.write("Verifying data integrity...")
        
        issues = []
        
        for week in weeks:
            # Check that all golfer matchups have corresponding rounds
            golfer_matchups = GolferMatchup.objects.filter(week=week)
            for matchup in golfer_matchups:
                if not Round.objects.filter(
                    golfer=matchup.golfer, 
                    week=week, 
                    golfer_matchup=matchup
                ).exists():
                    issues.append(f"Week {week.number}: Missing round for {matchup.golfer.name}")
            
            # Check for duplicate rounds
            duplicate_rounds = Round.objects.filter(week=week).values(
                'golfer', 'golfer_matchup'
            ).annotate(
                count=models.Count('id')
            ).filter(count__gt=1)
            
            for duplicate in duplicate_rounds:
                issues.append(f"Week {week.number}: Duplicate rounds for {duplicate['golfer']}")
        
        if issues:
            self.stdout.write(self.style.WARNING("Data integrity issues found:"))
            for issue in issues:
                self.stdout.write(f"  - {issue}")
        else:
            self.stdout.write(self.style.SUCCESS("✓ Data integrity check passed"))
        
        return len(issues) == 0 