from django.core.management.base import BaseCommand, CommandError
from django.db import connections
from django.db.models import Q
from main.models import *
from datetime import datetime
import sqlite3
import os


class Command(BaseCommand):
    help = 'Migrate data from old live site database to new structure'
    
    # Name conversion rules for old database to new database
    NAME_CONVERSIONS = {
        'Dan Mcconomy': 'Dan McConomy',  # Fix case sensitivity issue
    }

    def add_arguments(self, parser):
        parser.add_argument(
            '--old-db',
            type=str,
            default='old.sqlite3',
            help='Path to old database file (default: old.sqlite3)'
        )
        parser.add_argument(
            '--year',
            type=int,
            help='Year to migrate (default: latest year in old database)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be migrated without actually doing it'
        )
        parser.add_argument(
            '--week',
            type=int,
            help='Migrate only a specific week'
        )
        parser.add_argument(
            '--week-range',
            type=str,
            help='Migrate a range of weeks (e.g., "4-9" for weeks 4 through 9)'
        )
        parser.add_argument(
            '--undo',
            action='store_true',
            help='Undo the migration (remove migrated data)'
        )

    def handle(self, *args, **options):
        old_db_path = options['old_db']
        target_year = options['year'] or 2025  # Default to 2025
        dry_run = options['dry_run']
        specific_week = options['week']
        week_range = options['week_range']
        undo = options['undo']

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

        if undo:
            # Undo migration doesn't need the old database
            if week_range:
                self.perform_undo_range(target_year, start_week, end_week, dry_run)
            else:
                self.perform_undo(target_year, specific_week, dry_run)
            return

        if not os.path.exists(old_db_path):
            raise CommandError(f"Old database file not found: {old_db_path}")

        self.stdout.write(f"Connecting to old database: {old_db_path}")
        
        # Connect to old database
        old_conn = sqlite3.connect(old_db_path)
        old_conn.row_factory = sqlite3.Row  # This allows column access by name
        
        try:
            self.stdout.write(f"Migrating data for year: {target_year}")
            
            # Check what weeks already exist in new database
            existing_weeks = set(Week.objects.filter(season__year=target_year).values_list('number', flat=True))
            self.stdout.write(f"Existing weeks in new database: {sorted(existing_weeks)}")

            if dry_run:
                self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made"))
                if week_range:
                    self.dry_run_migration_range(old_conn, target_year, start_week, end_week, existing_weeks)
                else:
                    self.dry_run_migration(old_conn, target_year, specific_week, existing_weeks)
            else:
                if week_range:
                    self.perform_migration_range(old_conn, target_year, start_week, end_week, existing_weeks)
                else:
                    self.perform_migration(old_conn, target_year, specific_week, existing_weeks)

        finally:
            old_conn.close()

    def dry_run_migration(self, old_conn, year, specific_week, existing_weeks):
        """Show what would be migrated without making changes"""
        cursor = old_conn.cursor()
        
        # Get weeks to process (week 4+ or specific week)
        if specific_week:
            weeks_to_process = [specific_week]
        else:
            # Get all weeks 4+ that have matchups and scores
            cursor.execute("""
                SELECT DISTINCT m.week 
                FROM main_matchup m 
                WHERE m.year = ? AND m.week >= 4 
                AND EXISTS (SELECT 1 FROM main_score s WHERE s.year = m.year AND s.week = m.week)
                ORDER BY m.week
            """, (year,))
            weeks_to_process = [row[0] for row in cursor.fetchall()]
        
        self.stdout.write(f"Found {len(weeks_to_process)} weeks to process: {weeks_to_process}")
        
        # Count subs (only for new golfers)
        sub_golfer_names = set()
        cursor.execute("SELECT DISTINCT sub_id FROM main_subrecord WHERE year = ? AND week >= 4", (year,))
        sub_ids = [row[0] for row in cursor.fetchall()]
        for sub_id in sub_ids:
            cursor.execute("SELECT name FROM main_golfer WHERE id = ?", (sub_id,))
            sub_name = cursor.fetchone()[0]
            sub_golfer_names.add(sub_name)
        
        # Count existing golfers that are subs
        existing_golfer_names = set(Golfer.objects.values_list('name', flat=True))
        new_sub_golfers = sub_golfer_names - existing_golfer_names
        
        # Count matchups needed
        if weeks_to_process:
            placeholders = ','.join(['?' for _ in weeks_to_process])
            cursor.execute(f"SELECT COUNT(*) FROM main_matchup WHERE year = ? AND week IN ({placeholders})", (year,) + tuple(weeks_to_process))
            matchup_count = cursor.fetchone()[0]
            
            # Count subs
            cursor.execute(f"SELECT COUNT(*) FROM main_subrecord WHERE year = ? AND week IN ({placeholders})", (year,) + tuple(weeks_to_process))
            sub_count = cursor.fetchone()[0]
            
            # Count scores
            cursor.execute(f"SELECT COUNT(*) FROM main_score WHERE year = ? AND week IN ({placeholders})", (year,) + tuple(weeks_to_process))
            score_count = cursor.fetchone()[0]
            
            # Check each week individually
            self.stdout.write("\nPer-week breakdown:")
            for week in weeks_to_process:
                cursor.execute("SELECT COUNT(*) FROM main_matchup WHERE year = ? AND week = ?", (year, week))
                week_matchups = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM main_subrecord WHERE year = ? AND week = ?", (year, week))
                week_subs = cursor.fetchone()[0]
                cursor.execute("SELECT COUNT(*) FROM main_score WHERE year = ? AND week = ?", (year, week))
                week_scores = cursor.fetchone()[0]
                
                status = "✓" if week_matchups > 0 and week_scores > 0 else "✗"
                sub_status = f"{week_subs} subs" if week_subs > 0 else "no subs"
                self.stdout.write(f"  Week {week}: {status} {week_matchups} matchups, {week_scores} scores, {sub_status}")
        else:
            matchup_count = sub_count = score_count = 0
        
        self.stdout.write(f"\nWould migrate for weeks {weeks_to_process}:")
        self.stdout.write(f"  - {len(new_sub_golfers)} new golfers (subs only)")
        self.stdout.write(f"  - {len(weeks_to_process)} weeks")
        self.stdout.write(f"  - {matchup_count} matchups")
        self.stdout.write(f"  - {sub_count} subs")
        self.stdout.write(f"  - {score_count} scores")
        
        if new_sub_golfers:
            self.stdout.write(f"  - New golfers to create: {', '.join(new_sub_golfers)}")
        
        if specific_week:
            self.stdout.write(f"  - Only week {specific_week}")

    def perform_migration(self, old_conn, year, specific_week, existing_weeks):
        """Actually perform the migration"""
        cursor = old_conn.cursor()
        
        # Disable signals during migration to prevent premature round generation
        from django.db.models.signals import post_save
        from main.signals import score_updated
        post_save.disconnect(score_updated, sender=Score)
        
        try:
            self.stdout.write(self.style.SUCCESS(f"Starting migration for year {year}"))
            
            # Step 1: Create or get season
            season, created = Season.objects.get_or_create(year=year)
            if created:
                self.stdout.write(f"✓ Created season {year}")
            else:
                self.stdout.write(f"✓ Using existing season {year}")

            # Step 2: Create subs as golfers (only if they don't exist)
            self.stdout.write("\nStep 2: Creating sub golfers...")
            self.create_sub_golfers(cursor, year)
            
            # Step 3: Migrate weeks (week 4+ only)
            self.stdout.write("\nStep 3: Migrating weeks...")
            weeks = self.migrate_weeks(cursor, year, season, specific_week, existing_weeks)
            
            # Step 4: Migrate matchups (week 4+ only)
            self.stdout.write("\nStep 4: Migrating matchups...")
            self.migrate_matchups(cursor, year, season, weeks, specific_week)
            
            # Step 5: Migrate subs (week 4+ only)
            self.stdout.write("\nStep 5: Migrating subs...")
            self.migrate_subs(cursor, year, season, weeks, specific_week)
            
            # Step 6: Migrate scores and create rounds (week 4+ only)
            self.stdout.write("\nStep 6: Migrating scores...")
            self.migrate_scores_and_rounds(cursor, year, season, weeks, specific_week)
            
            # Step 7: Generate handicaps and golfer matchups
            self.stdout.write("\nStep 7: Generating handicaps and matchups...")
            self.generate_handicaps_and_matchups(season)
            
            # Print summary
            self.stdout.write("\n📊 Migration Summary:")
            total_weeks = len(weeks)
            total_subs = Sub.objects.filter(week__in=weeks.values()).count()
            total_scores = Score.objects.filter(week__in=weeks.values()).count()
            total_matchups = Matchup.objects.filter(week__in=weeks.values()).count()
            
            self.stdout.write(f"  • {total_weeks} weeks migrated")
            self.stdout.write(f"  • {total_matchups} matchups created")
            self.stdout.write(f"  • {total_subs} sub records created")
            self.stdout.write(f"  • {total_scores} scores migrated")
            
            self.stdout.write(self.style.SUCCESS("\n🎉 Migration completed successfully!"))
            
        finally:
            # Re-enable signals after migration
            post_save.connect(score_updated, sender=Score)

    def migrate_holes(self, cursor, year, season):
        """Migrate hole data"""
        cursor.execute("SELECT * FROM main_hole WHERE year = ? ORDER BY hole", (year,))
        holes = cursor.fetchall()
        
        for hole_data in holes:
            hole, created = Hole.objects.get_or_create(
                season=season,
                number=hole_data['hole'],
                defaults={
                    'par': hole_data['par'],
                    'handicap': hole_data['handicap'],
                    'handicap9': hole_data['handicap9'],
                    'yards': hole_data['yards'],
                }
            )
            if created:
                self.stdout.write(f"  Created hole {hole_data['hole']}")
        
        self.stdout.write(f"Migrated {len(holes)} holes")

    def create_sub_golfers(self, cursor, year):
        """Create golfers only if they are subs and don't exist"""
        # Get all sub golfer IDs for week 4+ (weeks with actual data only)
        cursor.execute("""
            SELECT DISTINCT sr.sub_id 
            FROM main_subrecord sr 
            WHERE sr.year = ? AND sr.week >= 4 
            AND EXISTS (SELECT 1 FROM main_score s WHERE s.year = sr.year AND s.week = sr.week)
        """, (year,))
        sub_ids = [row[0] for row in cursor.fetchall()]
        
        # Get existing golfer names
        existing_golfer_names = set(Golfer.objects.values_list('name', flat=True))
        
        new_golfers_created = 0
        for sub_id in sub_ids:
            cursor.execute("SELECT name FROM main_golfer WHERE id = ?", (sub_id,))
            sub_name = cursor.fetchone()[0]
            
            # Apply name conversion if needed
            if sub_name in self.NAME_CONVERSIONS:
                sub_name = self.NAME_CONVERSIONS[sub_name]
                self.stdout.write(f"  Converting sub golfer name: {sub_name}")
            
            if sub_name not in existing_golfer_names:
                golfer, created = Golfer.objects.get_or_create(name=sub_name)
                if created:
                    self.stdout.write(f"  Created sub golfer: {sub_name}")
                    new_golfers_created += 1
        
        self.stdout.write(f"Created {new_golfers_created} new sub golfers")

    def migrate_weeks(self, cursor, year, season, specific_week, existing_weeks):
        """Migrate weeks (week 4+ only)"""
        if specific_week:
            if specific_week in existing_weeks:
                self.stdout.write(f"Week {specific_week} already exists, skipping")
                return {specific_week: Week.objects.get(season=season, number=specific_week, rained_out=False)}
            
            cursor.execute("SELECT DISTINCT week FROM main_matchup WHERE year = ? AND week = ?", (year, specific_week))
        else:
            # Only get weeks 4+ that don't already exist and have actual data
            cursor.execute("""
                SELECT DISTINCT m.week 
                FROM main_matchup m 
                WHERE m.year = ? AND m.week >= 4 
                AND EXISTS (SELECT 1 FROM main_score s WHERE s.year = m.year AND s.week = m.week)
                ORDER BY m.week
            """, (year,))
        
        week_numbers = [row[0] for row in cursor.fetchall()]
        weeks = {}
        
        for week_num in week_numbers:
            # Skip if week already exists
            if week_num in existing_weeks:
                weeks[week_num] = Week.objects.get(season=season, number=week_num, rained_out=False)
                continue
            
            # Create week with default date (we'll use a placeholder since we don't have actual dates)
            # You may want to manually set the correct dates after migration
            week, created = Week.objects.get_or_create(
                season=season,
                number=week_num,
                defaults={
                    'date': datetime(2025, 1, 1),  # Placeholder date
                    'rained_out': False,  # Default to not rained out
                    'is_front': True,  # Default, will be updated from matchups
                    'num_scores': 0,  # Will be calculated
                }
            )
            if created:
                self.stdout.write(f"  Created week {week_num}")
            weeks[week_num] = week
        
        self.stdout.write(f"Processed {len(weeks)} weeks")
        return weeks

    def migrate_matchups(self, cursor, year, season, weeks, specific_week):
        """Migrate matchups (week 4+ only) with team mapping by golfer names"""
        if specific_week:
            cursor.execute("SELECT * FROM main_matchup WHERE year = ? AND week = ?", (year, specific_week))
        else:
            cursor.execute("""
                SELECT m.* 
                FROM main_matchup m 
                WHERE m.year = ? AND m.week >= 4 
                AND EXISTS (SELECT 1 FROM main_score s WHERE s.year = m.year AND s.week = m.week)
                ORDER BY m.week
            """, (year,))
        
        matchups = cursor.fetchall()
        matchups_created = 0
        
        # Build a mapping of new teams by golfer name set for this season
        from main.models import Team
        new_teams = list(Team.objects.filter(season=season).prefetch_related('golfers'))
        team_golfer_name_map = {}
        for team in new_teams:
            golfer_names = tuple(sorted(g.name.lower() for g in team.golfers.all()))
            team_golfer_name_map[golfer_names] = team
        
        for matchup_data in matchups:
            week_num = matchup_data['week']
            if week_num not in weeks:
                continue
            week = weeks[week_num]
            # Update week front/back info
            week.is_front = matchup_data['front']
            week.save()
            # Get golfer names for each team in the old DB
            team1_id = matchup_data['team1']
            team2_id = matchup_data['team2']
            cursor.execute("SELECT name FROM main_golfer WHERE team = ? AND year = ? ORDER BY name", (team1_id, year))
            team1_golfers = [row[0] for row in cursor.fetchall()]
            cursor.execute("SELECT name FROM main_golfer WHERE team = ? AND year = ? ORDER BY name", (team2_id, year))
            team2_golfers = [row[0] for row in cursor.fetchall()]
            team1_key = tuple(sorted(name.lower() for name in team1_golfers))
            team2_key = tuple(sorted(name.lower() for name in team2_golfers))
            team1 = team_golfer_name_map.get(team1_key)
            team2 = team_golfer_name_map.get(team2_key)
            if not team1 or not team2:
                self.stdout.write(f"  Warning: Could not match teams for matchup in week {week_num}:\n    Old team1 golfers: {team1_golfers}\n    Old team2 golfers: {team2_golfers}")
                continue
            # Check if a matchup with these teams already exists for this week
            existing = Matchup.objects.filter(week=week, teams=team1).filter(teams=team2)
            if not existing.exists():
                matchup = Matchup.objects.create(week=week)
                matchup.teams.set([team1, team2])
                self.stdout.write(f"  Created matchup for week {week_num}: {team1} vs {team2}")
                matchups_created += 1
            else:
                self.stdout.write(f"  Skipped duplicate matchup for week {week_num}: {team1} vs {team2}")
        self.stdout.write(f"Migrated {matchups_created} new matchups from {len(matchups)} total matchup records")

    def migrate_subs(self, cursor, year, season, weeks, specific_week):
        """Migrate subs (week 4+ only)"""
        if specific_week:
            cursor.execute("SELECT * FROM main_subrecord WHERE year = ? AND week = ?", (year, specific_week))
        else:
            # Only get subs for weeks that have actual data
            cursor.execute("""
                SELECT sr.* 
                FROM main_subrecord sr 
                WHERE sr.year = ? AND sr.week >= 4 
                AND EXISTS (SELECT 1 FROM main_score s WHERE s.year = sr.year AND s.week = sr.week)
                ORDER BY sr.week
            """, (year,))
        
        subs = cursor.fetchall()
        
        self.stdout.write(f"  Found {len(subs)} sub records to process")
        
        for sub_data in subs:
            week_num = sub_data['week']
            if week_num not in weeks:
                continue
                
            week = weeks[week_num]
            
            # Get or create absent golfer
            cursor.execute("SELECT name FROM main_golfer WHERE id = ?", (sub_data['absent_id'],))
            absent_name = cursor.fetchone()['name']
            
            # Apply name conversion if needed
            if absent_name in self.NAME_CONVERSIONS:
                absent_name = self.NAME_CONVERSIONS[absent_name]
                self.stdout.write(f"  Converting absent golfer name: {absent_name}")
            
            absent_golfer, _ = Golfer.objects.get_or_create(name=absent_name)
            
            # Get or create sub golfer
            cursor.execute("SELECT name FROM main_golfer WHERE id = ?", (sub_data['sub_id'],))
            sub_name = cursor.fetchone()['name']
            
            # Apply name conversion if needed
            if sub_name in self.NAME_CONVERSIONS:
                sub_name = self.NAME_CONVERSIONS[sub_name]
                self.stdout.write(f"  Converting sub golfer name: {sub_name}")
            
            sub_golfer, _ = Golfer.objects.get_or_create(name=sub_name)
            
            # Check if the "sub" is actually a teammate (invalid sub)
            cursor.execute("SELECT team FROM main_golfer WHERE id = ? AND year = ?", (sub_data['absent_id'], year))
            absent_team = cursor.fetchone()['team']
            cursor.execute("SELECT team FROM main_golfer WHERE id = ? AND year = ?", (sub_data['sub_id'], year))
            sub_team = cursor.fetchone()['team']
            
            if absent_team == sub_team:
                # This is an invalid sub - teammate can't sub for teammate
                # Create a no_sub record instead
                sub, created = Sub.objects.get_or_create(
                    week=week,
                    absent_golfer=absent_golfer,
                    defaults={'sub_golfer': None, 'no_sub': True}
                )
                
                if created:
                    self.stdout.write(f"  ✓ Created no_sub record: {absent_name} absent with no sub (invalid teammate sub) in week {week_num}")
            else:
                # Valid sub - create normal sub record
                sub, created = Sub.objects.get_or_create(
                    week=week,
                    absent_golfer=absent_golfer,
                    sub_golfer=sub_golfer,
                    defaults={'no_sub': False}
                )
                
                if created:
                    self.stdout.write(f"  ✓ Created sub: {sub_name} for {absent_name} in week {week_num}")
        
        self.stdout.write(f"✓ Migrated {len(subs)} subs")
        
        if len(subs) == 0:
            self.stdout.write("  Note: No subs found - this is normal if all golfers were present")

    def migrate_scores_and_rounds(self, cursor, year, season, weeks, specific_week):
        """Migrate scores (week 4+ only)"""
        if specific_week:
            cursor.execute("SELECT * FROM main_score WHERE year = ? AND week = ? ORDER BY golfer, hole", (year, specific_week))
        else:
            # Only get scores for weeks that have actual data
            cursor.execute("""
                SELECT s.* 
                FROM main_score s 
                WHERE s.year = ? AND s.week >= 4 
                AND EXISTS (SELECT 1 FROM main_round r WHERE r.year = s.year AND r.week = s.week)
                ORDER BY s.week, s.golfer, s.hole
            """, (year,))
        
        scores = cursor.fetchall()
        
        # Group scores by week, golfer, and hole
        score_groups = {}
        for score_data in scores:
            week_num = score_data['week']
            golfer_id = score_data['golfer']
            hole_num = score_data['hole']
            
            if week_num not in weeks:
                continue
                
            key = (week_num, golfer_id)
            if key not in score_groups:
                score_groups[key] = {}
            score_groups[key][hole_num] = score_data
        
        # Process each golfer's round
        for (week_num, golfer_id), hole_scores in score_groups.items():
            week = weeks[week_num]
            
            # Get golfer
            cursor.execute("SELECT name FROM main_golfer WHERE id = ?", (golfer_id,))
            golfer_name = cursor.fetchone()['name']
            
            # Apply name conversion if needed
            if golfer_name in self.NAME_CONVERSIONS:
                golfer_name = self.NAME_CONVERSIONS[golfer_name]
                self.stdout.write(f"  Converting golfer name: {golfer_name}")
            
            golfer, _ = Golfer.objects.get_or_create(name=golfer_name)
            
            # Get round data from old database
            cursor.execute("SELECT * FROM main_round WHERE year = ? AND week = ? AND golfer = ?", 
                         (year, week_num, golfer_id))
            round_data = cursor.fetchone()
            
            if not round_data:
                continue
            
            # Create handicap
            handicap, _ = Handicap.objects.get_or_create(
                golfer=golfer,
                week=week,
                defaults={'handicap': round_data['hcp']}
            )
            
            # Create scores
            for hole_num, score_data in hole_scores.items():
                hole = Hole.objects.get(season=season, number=hole_num)
                
                score, created = Score.objects.get_or_create(
                    golfer=golfer,
                    week=week,
                    hole=hole,
                    defaults={'score': score_data['score']}
                )
            
            # Note: Rounds will be created by generate_rounds() after golfer matchups are generated
        
        self.stdout.write(f"✓ Migrated {len(scores)} scores")
        
        if len(scores) == 0:
            self.stdout.write("  Warning: No scores found - this may indicate an issue")

    def generate_handicaps_and_matchups(self, season):
        """Generate handicaps and golfer matchups for the season"""
        from main.helper import calculate_and_save_handicaps_for_season, generate_rounds, generate_golfer_matchups
        
        self.stdout.write("Generating handicaps...")
        try:
            calculate_and_save_handicaps_for_season(season)
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Warning: Error generating handicaps: {e}"))
        
        self.stdout.write("Generating golfer matchups...")
        try:
            # Generate golfer matchups for each week
            for week in Week.objects.filter(season=season):
                self.stdout.write(f"  Generating golfer matchups for week {week.number}...")
                generate_golfer_matchups(week)
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Warning: Error generating golfer matchups: {e}"))
            self.stdout.write("Migration completed, but golfer matchup generation had issues.")
        
        self.stdout.write("Generating rounds...")
        try:
            generate_rounds(season)
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Warning: Error generating rounds: {e}"))
            self.stdout.write("Migration completed, but round generation had issues. You may need to manually generate rounds.")
        
        self.stdout.write("✓ Handicaps, golfer matchups, and rounds generated")

    def perform_undo(self, year, specific_week, dry_run):
        """Undo the migration by removing migrated data"""
        try:
            season = Season.objects.get(year=year)
        except Season.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"No season found for year {year}"))
            return

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made"))
            self.dry_run_undo(season, specific_week)
        else:
            self.undo_migration(season, specific_week)

    def dry_run_undo(self, season, specific_week):
        """Show what would be undone without making changes"""
        # Determine weeks to undo
        if specific_week:
            weeks_to_undo = [specific_week] if specific_week >= 4 else []
        else:
            weeks_to_undo = list(Week.objects.filter(season=season, number__gte=4).values_list('number', flat=True))

        if not weeks_to_undo:
            self.stdout.write("No weeks to undo (only week 4+ can be undone)")
            return

        # Count what would be removed
        weeks = Week.objects.filter(season=season, number__in=weeks_to_undo)
        
        # Count subs
        sub_count = Sub.objects.filter(week__in=weeks).count()
        
        # Count scores
        score_count = Score.objects.filter(week__in=weeks).count()
        
        # Count rounds
        round_count = Round.objects.filter(week__in=weeks).count()
        
        # Count handicaps
        handicap_count = Handicap.objects.filter(week__in=weeks).count()
        
        # Count golfer matchups
        golfer_matchup_count = GolferMatchup.objects.filter(week__in=weeks).count()
        
        # Count matchups
        matchup_count = Matchup.objects.filter(week__in=weeks).count()
        
        # Count points
        points_count = Points.objects.filter(week__in=weeks).count()
        
        # Count sub golfers (only if they're not used elsewhere)
        sub_golfers = set()
        for sub in Sub.objects.filter(week__in=weeks):
            if not Sub.objects.filter(sub_golfer=sub.sub_golfer).exclude(week__in=weeks).exists():
                sub_golfers.add(sub.sub_golfer.name)
        
        self.stdout.write(f"Would undo migration for weeks {weeks_to_undo}:")
        self.stdout.write(f"  - {len(weeks_to_undo)} weeks")
        self.stdout.write(f"  - {matchup_count} matchups")
        self.stdout.write(f"  - {sub_count} subs")
        self.stdout.write(f"  - {score_count} scores")
        self.stdout.write(f"  - {round_count} rounds")
        self.stdout.write(f"  - {handicap_count} handicaps")
        self.stdout.write(f"  - {golfer_matchup_count} golfer matchups")
        self.stdout.write(f"  - {points_count} points")
        
        if sub_golfers:
            self.stdout.write(f"  - {len(sub_golfers)} sub golfers would be removed: {', '.join(sub_golfers)}")
        
        if specific_week:
            self.stdout.write(f"  - Only week {specific_week}")

    def undo_migration(self, season, specific_week):
        """Actually undo the migration"""
        # Determine weeks to undo
        if specific_week:
            if specific_week < 4:
                self.stdout.write(self.style.ERROR(f"Cannot undo week {specific_week} (only week 4+ can be undone)"))
                return
            weeks_to_undo = [specific_week]
        else:
            weeks_to_undo = list(Week.objects.filter(season=season, number__gte=4).values_list('number', flat=True))

        if not weeks_to_undo:
            self.stdout.write("No weeks to undo (only week 4+ can be undone)")
            return

        weeks = Week.objects.filter(season=season, number__in=weeks_to_undo)
        
        # Step 1: Remove points
        points_deleted, _ = Points.objects.filter(week__in=weeks).delete()
        self.stdout.write(f"  Removed {points_deleted} points")
        
        # Step 2: Remove golfer matchups
        golfer_matchup_deleted, _ = GolferMatchup.objects.filter(week__in=weeks).delete()
        self.stdout.write(f"  Removed {golfer_matchup_deleted} golfer matchups")
        
        # Step 3: Remove rounds
        round_deleted, _ = Round.objects.filter(week__in=weeks).delete()
        self.stdout.write(f"  Removed {round_deleted} rounds")
        
        # Step 4: Remove scores
        score_deleted, _ = Score.objects.filter(week__in=weeks).delete()
        self.stdout.write(f"  Removed {score_deleted} scores")
        
        # Step 5: Remove handicaps
        handicap_deleted, _ = Handicap.objects.filter(week__in=weeks).delete()
        self.stdout.write(f"  Removed {handicap_deleted} handicaps")
        
        # Step 6: Remove subs
        sub_deleted, _ = Sub.objects.filter(week__in=weeks).delete()
        self.stdout.write(f"  Removed {sub_deleted} subs")
        
        # Step 7: Remove matchups
        matchup_deleted, _ = Matchup.objects.filter(week__in=weeks).delete()
        self.stdout.write(f"  Removed {matchup_deleted} matchups")
        
        # Step 8: Remove weeks
        week_deleted, _ = weeks.delete()
        self.stdout.write(f"  Removed {week_deleted} weeks")
        
        # Step 9: Remove sub golfers that are no longer used
        self.remove_unused_sub_golfers()
        
        self.stdout.write(self.style.SUCCESS("Undo completed successfully!"))

    def remove_unused_sub_golfers(self):
        """Remove golfers that were only created as subs and are no longer used"""
        # Get all golfers that are not on any teams
        team_golfers = set()
        for team in Team.objects.all():
            team_golfers.update(team.golfers.values_list('id', flat=True))
        
        # Get all golfers that are subs
        sub_golfers = set()
        for sub in Sub.objects.all():
            if sub.sub_golfer:
                sub_golfers.add(sub.sub_golfer.id)
        
        # Find golfers that are only subs and not on teams
        unused_sub_golfers = sub_golfers - team_golfers
        
        # Remove them
        if unused_sub_golfers:
            deleted_count = Golfer.objects.filter(id__in=unused_sub_golfers).delete()[0]
            self.stdout.write(f"  Removed {deleted_count} unused sub golfers")

    def perform_migration_range(self, old_conn, year, start_week, end_week, existing_weeks):
        """Perform migration for a range of weeks"""
        cursor = old_conn.cursor()
        
        # Disable signals during migration to prevent premature round generation
        from django.db.models.signals import post_save
        from main.signals import score_updated
        post_save.disconnect(score_updated, sender=Score)
        
        try:
            # Step 1: Create or get season
            season, created = Season.objects.get_or_create(year=year)
            if created:
                self.stdout.write(f"Created season {year}")
            else:
                self.stdout.write(f"Using existing season {year}")

            # Step 2: Create subs as golfers (only if they don't exist)
            self.create_sub_golfers_range(cursor, year, start_week, end_week)
            
            # Step 3: Migrate weeks in range
            weeks = self.migrate_weeks_range(cursor, year, season, start_week, end_week, existing_weeks)
            
            # Step 4: Migrate matchups in range
            self.migrate_matchups_range(cursor, year, season, weeks, start_week, end_week)
            
            # Step 5: Migrate subs in range
            self.migrate_subs_range(cursor, year, season, weeks, start_week, end_week)
            
            # Step 6: Migrate scores and create rounds in range
            self.migrate_scores_and_rounds_range(cursor, year, season, weeks, start_week, end_week)
            
            # Step 7: Generate handicaps and golfer matchups
            self.generate_handicaps_and_matchups(season)
            
            self.stdout.write(self.style.SUCCESS(f"Migration completed successfully for weeks {start_week}-{end_week}!"))
            
        finally:
            # Re-enable signals after migration
            post_save.connect(score_updated, sender=Score)

    def dry_run_migration_range(self, old_conn, year, start_week, end_week, existing_weeks):
        """Show what would be migrated for a range of weeks without making changes"""
        cursor = old_conn.cursor()
        
        # Get weeks to process in range
        weeks_to_process = list(range(start_week, end_week + 1))
        
        # Count subs (only for new golfers)
        sub_golfer_names = set()
        cursor.execute("SELECT DISTINCT sub_id FROM main_subrecord WHERE year = ? AND week BETWEEN ? AND ?", (year, start_week, end_week))
        sub_ids = [row[0] for row in cursor.fetchall()]
        for sub_id in sub_ids:
            cursor.execute("SELECT name FROM main_golfer WHERE id = ?", (sub_id,))
            sub_name = cursor.fetchone()[0]
            sub_golfer_names.add(sub_name)
        
        # Count existing golfers that are subs
        existing_golfer_names = set(Golfer.objects.values_list('name', flat=True))
        new_sub_golfers = sub_golfer_names - existing_golfer_names
        
        # Count matchups needed
        cursor.execute("SELECT COUNT(*) FROM main_matchup WHERE year = ? AND week BETWEEN ? AND ?", (year, start_week, end_week))
        matchup_count = cursor.fetchone()[0]
        
        # Count subs
        cursor.execute("SELECT COUNT(*) FROM main_subrecord WHERE year = ? AND week BETWEEN ? AND ?", (year, start_week, end_week))
        sub_count = cursor.fetchone()[0]
        
        # Count scores
        cursor.execute("SELECT COUNT(*) FROM main_score WHERE year = ? AND week BETWEEN ? AND ?", (year, start_week, end_week))
        score_count = cursor.fetchone()[0]
        
        self.stdout.write(f"Would migrate for weeks {start_week}-{end_week}:")
        self.stdout.write(f"  - {len(new_sub_golfers)} new golfers (subs only)")
        self.stdout.write(f"  - {len(weeks_to_process)} weeks")
        self.stdout.write(f"  - {matchup_count} matchups")
        self.stdout.write(f"  - {sub_count} subs")
        self.stdout.write(f"  - {score_count} scores")
        
        if new_sub_golfers:
            self.stdout.write(f"  - New golfers to create: {', '.join(new_sub_golfers)}")

    def create_sub_golfers_range(self, cursor, year, start_week, end_week):
        """Create golfers only if they are subs and don't exist for a range of weeks"""
        # Get all sub golfer IDs for the range
        cursor.execute("""
            SELECT DISTINCT sr.sub_id 
            FROM main_subrecord sr 
            WHERE sr.year = ? AND sr.week BETWEEN ? AND ?
            AND EXISTS (SELECT 1 FROM main_score s WHERE s.year = sr.year AND s.week = sr.week)
        """, (year, start_week, end_week))
        sub_ids = [row[0] for row in cursor.fetchall()]
        
        # Get existing golfer names
        existing_golfer_names = set(Golfer.objects.values_list('name', flat=True))
        
        new_golfers_created = 0
        for sub_id in sub_ids:
            cursor.execute("SELECT name FROM main_golfer WHERE id = ?", (sub_id,))
            sub_name = cursor.fetchone()[0]
            
            # Apply name conversion if needed
            if sub_name in self.NAME_CONVERSIONS:
                sub_name = self.NAME_CONVERSIONS[sub_name]
                self.stdout.write(f"  Converting sub golfer name: {sub_name}")
            
            if sub_name not in existing_golfer_names:
                golfer, created = Golfer.objects.get_or_create(name=sub_name)
                if created:
                    self.stdout.write(f"  Created sub golfer: {sub_name}")
                    new_golfers_created += 1
        
        self.stdout.write(f"Created {new_golfers_created} new sub golfers")

    def migrate_weeks_range(self, cursor, year, season, start_week, end_week, existing_weeks):
        """Migrate weeks in a range"""
        weeks_to_process = list(range(start_week, end_week + 1))
        weeks = {}
        
        for week_num in weeks_to_process:
            # Skip if week already exists
            if week_num in existing_weeks:
                weeks[week_num] = Week.objects.get(season=season, number=week_num, rained_out=False)
                continue
            
            # Create week with default date
            week, created = Week.objects.get_or_create(
                season=season,
                number=week_num,
                defaults={
                    'date': datetime(2025, 1, 1),  # Placeholder date
                    'rained_out': False,
                    'is_front': True,
                    'num_scores': 0,
                }
            )
            if created:
                self.stdout.write(f"  Created week {week_num}")
            weeks[week_num] = week
        
        self.stdout.write(f"Processed {len(weeks)} weeks")
        return weeks

    def migrate_matchups_range(self, cursor, year, season, weeks, start_week, end_week):
        """Migrate matchups for a range of weeks"""
        cursor.execute("SELECT * FROM main_matchup WHERE year = ? AND week BETWEEN ? AND ?", (year, start_week, end_week))
        matchups = cursor.fetchall()
        matchups_created = 0
        
        # Build a mapping of new teams by golfer name set for this season
        from main.models import Team
        new_teams = list(Team.objects.filter(season=season).prefetch_related('golfers'))
        team_golfer_name_map = {}
        for team in new_teams:
            golfer_names = tuple(sorted(g.name.lower() for g in team.golfers.all()))
            team_golfer_name_map[golfer_names] = team
        
        for matchup_data in matchups:
            week_num = matchup_data['week']
            if week_num not in weeks:
                continue
            week = weeks[week_num]
            
            # Update week front/back info
            week.is_front = matchup_data['front']
            week.save()
            
            # Get golfer names for each team in the old DB
            team1_id = matchup_data['team1']
            team2_id = matchup_data['team2']
            cursor.execute("SELECT name FROM main_golfer WHERE team = ? AND year = ? ORDER BY name", (team1_id, year))
            team1_golfers = [row[0] for row in cursor.fetchall()]
            cursor.execute("SELECT name FROM main_golfer WHERE team = ? AND year = ? ORDER BY name", (team2_id, year))
            team2_golfers = [row[0] for row in cursor.fetchall()]
            
            team1_key = tuple(sorted(name.lower() for name in team1_golfers))
            team2_key = tuple(sorted(name.lower() for name in team2_golfers))
            team1 = team_golfer_name_map.get(team1_key)
            team2 = team_golfer_name_map.get(team2_key)
            
            if not team1 or not team2:
                self.stdout.write(f"  Warning: Could not match teams for matchup in week {week_num}:\n    Old team1 golfers: {team1_golfers}\n    Old team2 golfers: {team2_golfers}")
                continue
            
            # Check if a matchup with these teams already exists for this week
            existing = Matchup.objects.filter(week=week, teams=team1).filter(teams=team2)
            if not existing.exists():
                matchup = Matchup.objects.create(week=week)
                matchup.teams.set([team1, team2])
                self.stdout.write(f"  Created matchup for week {week_num}: {team1} vs {team2}")
                matchups_created += 1
            else:
                self.stdout.write(f"  Skipped duplicate matchup for week {week_num}: {team1} vs {team2}")
        
        self.stdout.write(f"Migrated {matchups_created} new matchups from {len(matchups)} total matchup records")

    def migrate_subs_range(self, cursor, year, season, weeks, start_week, end_week):
        """Migrate subs for a range of weeks"""
        cursor.execute("SELECT * FROM main_subrecord WHERE year = ? AND week BETWEEN ? AND ?", (year, start_week, end_week))
        subs = cursor.fetchall()
        
        for sub_data in subs:
            week_num = sub_data['week']
            if week_num not in weeks:
                continue
                
            week = weeks[week_num]
            
            # Get or create absent golfer
            cursor.execute("SELECT name FROM main_golfer WHERE id = ?", (sub_data['absent_id'],))
            absent_name = cursor.fetchone()['name']
            
            # Apply name conversion if needed
            if absent_name in self.NAME_CONVERSIONS:
                absent_name = self.NAME_CONVERSIONS[absent_name]
                self.stdout.write(f"  Converting absent golfer name: {absent_name}")
            
            absent_golfer, _ = Golfer.objects.get_or_create(name=absent_name)
            
            # Get or create sub golfer
            cursor.execute("SELECT name FROM main_golfer WHERE id = ?", (sub_data['sub_id'],))
            sub_name = cursor.fetchone()['name']
            
            # Apply name conversion if needed
            if sub_name in self.NAME_CONVERSIONS:
                sub_name = self.NAME_CONVERSIONS[sub_name]
                self.stdout.write(f"  Converting sub golfer name: {sub_name}")
            
            sub_golfer, _ = Golfer.objects.get_or_create(name=sub_name)
            
            # Check if the "sub" is actually a teammate (invalid sub)
            cursor.execute("SELECT team FROM main_golfer WHERE id = ? AND year = ?", (sub_data['absent_id'], year))
            absent_team = cursor.fetchone()['team']
            cursor.execute("SELECT team FROM main_golfer WHERE id = ? AND year = ?", (sub_data['sub_id'], year))
            sub_team = cursor.fetchone()['team']
            
            if absent_team == sub_team:
                # This is an invalid sub - teammate can't sub for teammate
                # Create a no_sub record instead
                sub, created = Sub.objects.get_or_create(
                    week=week,
                    absent_golfer=absent_golfer,
                    defaults={'sub_golfer': None, 'no_sub': True}
                )
                
                if created:
                    self.stdout.write(f"  Created no_sub record: {absent_name} absent with no sub (invalid teammate sub) in week {week_num}")
            else:
                # Valid sub - create normal sub record
                sub, created = Sub.objects.get_or_create(
                    week=week,
                    absent_golfer=absent_golfer,
                    sub_golfer=sub_golfer,
                    defaults={'no_sub': False}
                )
                
                if created:
                    self.stdout.write(f"  Created sub: {sub_name} for {absent_name} in week {week_num}")
        
        self.stdout.write(f"Migrated {len(subs)} subs")

    def migrate_scores_and_rounds_range(self, cursor, year, season, weeks, start_week, end_week):
        """Migrate scores for a range of weeks"""
        cursor.execute("SELECT * FROM main_score WHERE year = ? AND week BETWEEN ? AND ? ORDER BY week, golfer, hole", (year, start_week, end_week))
        scores = cursor.fetchall()
        
        # Group scores by week, golfer, and hole
        score_groups = {}
        for score_data in scores:
            week_num = score_data['week']
            golfer_id = score_data['golfer']
            hole_num = score_data['hole']
            
            if week_num not in weeks:
                continue
                
            key = (week_num, golfer_id)
            if key not in score_groups:
                score_groups[key] = {}
            score_groups[key][hole_num] = score_data
        
        # Process each golfer's round
        for (week_num, golfer_id), hole_scores in score_groups.items():
            week = weeks[week_num]
            
            # Get golfer
            cursor.execute("SELECT name FROM main_golfer WHERE id = ?", (golfer_id,))
            golfer_name = cursor.fetchone()['name']
            
            # Apply name conversion if needed
            if golfer_name in self.NAME_CONVERSIONS:
                golfer_name = self.NAME_CONVERSIONS[golfer_name]
                self.stdout.write(f"  Converting golfer name: {golfer_name}")
            
            golfer, _ = Golfer.objects.get_or_create(name=golfer_name)
            
            # Get round data from old database
            cursor.execute("SELECT * FROM main_round WHERE year = ? AND week = ? AND golfer = ?", 
                         (year, week_num, golfer_id))
            round_data = cursor.fetchone()
            
            if not round_data:
                continue
            
            # Create handicap
            handicap, _ = Handicap.objects.get_or_create(
                golfer=golfer,
                week=week,
                defaults={'handicap': round_data['hcp']}
            )
            
            # Create scores
            for hole_num, score_data in hole_scores.items():
                hole = Hole.objects.get(season=season, number=hole_num)
                
                score, created = Score.objects.get_or_create(
                    golfer=golfer,
                    week=week,
                    hole=hole,
                    defaults={'score': score_data['score']}
                )
        
        self.stdout.write(f"Migrated {len(scores)} scores")

    def perform_undo_range(self, year, start_week, end_week, dry_run):
        """Undo the migration for a range of weeks"""
        try:
            season = Season.objects.get(year=year)
        except Season.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"No season found for year {year}"))
            return

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made"))
            self.dry_run_undo_range(season, start_week, end_week)
        else:
            self.undo_migration_range(season, start_week, end_week)

    def dry_run_undo_range(self, season, start_week, end_week):
        """Show what would be undone for a range of weeks without making changes"""
        weeks_to_undo = list(range(start_week, end_week + 1))
        weeks_to_undo = [w for w in weeks_to_undo if w >= 4]  # Only week 4+ can be undone

        if not weeks_to_undo:
            self.stdout.write("No weeks to undo (only week 4+ can be undone)")
            return

        # Count what would be removed
        weeks = Week.objects.filter(season=season, number__in=weeks_to_undo)
        
        # Count subs
        sub_count = Sub.objects.filter(week__in=weeks).count()
        
        # Count scores
        score_count = Score.objects.filter(week__in=weeks).count()
        
        # Count rounds
        round_count = Round.objects.filter(week__in=weeks).count()
        
        # Count handicaps
        handicap_count = Handicap.objects.filter(week__in=weeks).count()
        
        # Count golfer matchups
        golfer_matchup_count = GolferMatchup.objects.filter(week__in=weeks).count()
        
        # Count matchups
        matchup_count = Matchup.objects.filter(week__in=weeks).count()
        
        # Count points
        points_count = Points.objects.filter(week__in=weeks).count()
        
        # Count sub golfers (only if they're not used elsewhere)
        sub_golfers = set()
        for sub in Sub.objects.filter(week__in=weeks):
            if not Sub.objects.filter(sub_golfer=sub.sub_golfer).exclude(week__in=weeks).exists():
                sub_golfers.add(sub.sub_golfer.name)
        
        self.stdout.write(f"Would undo migration for weeks {start_week}-{end_week}:")
        self.stdout.write(f"  - {len(weeks_to_undo)} weeks")
        self.stdout.write(f"  - {matchup_count} matchups")
        self.stdout.write(f"  - {sub_count} subs")
        self.stdout.write(f"  - {score_count} scores")
        self.stdout.write(f"  - {round_count} rounds")
        self.stdout.write(f"  - {handicap_count} handicaps")
        self.stdout.write(f"  - {golfer_matchup_count} golfer matchups")
        self.stdout.write(f"  - {points_count} points")
        
        if sub_golfers:
            self.stdout.write(f"  - {len(sub_golfers)} sub golfers would be removed: {', '.join(sub_golfers)}")

    def undo_migration_range(self, season, start_week, end_week):
        """Actually undo the migration for a range of weeks"""
        weeks_to_undo = list(range(start_week, end_week + 1))
        weeks_to_undo = [w for w in weeks_to_undo if w >= 4]  # Only week 4+ can be undone

        if not weeks_to_undo:
            self.stdout.write("No weeks to undo (only week 4+ can be undone)")
            return

        weeks = Week.objects.filter(season=season, number__in=weeks_to_undo)
        
        # Step 1: Remove points
        points_deleted, _ = Points.objects.filter(week__in=weeks).delete()
        self.stdout.write(f"  Removed {points_deleted} points")
        
        # Step 2: Remove golfer matchups
        golfer_matchup_deleted, _ = GolferMatchup.objects.filter(week__in=weeks).delete()
        self.stdout.write(f"  Removed {golfer_matchup_deleted} golfer matchups")
        
        # Step 3: Remove rounds
        round_deleted, _ = Round.objects.filter(week__in=weeks).delete()
        self.stdout.write(f"  Removed {round_deleted} rounds")
        
        # Step 4: Remove scores
        score_deleted, _ = Score.objects.filter(week__in=weeks).delete()
        self.stdout.write(f"  Removed {score_deleted} scores")
        
        # Step 5: Remove handicaps
        handicap_deleted, _ = Handicap.objects.filter(week__in=weeks).delete()
        self.stdout.write(f"  Removed {handicap_deleted} handicaps")
        
        # Step 6: Remove subs
        sub_deleted, _ = Sub.objects.filter(week__in=weeks).delete()
        self.stdout.write(f"  Removed {sub_deleted} subs")
        
        # Step 7: Remove matchups
        matchup_deleted, _ = Matchup.objects.filter(week__in=weeks).delete()
        self.stdout.write(f"  Removed {matchup_deleted} matchups")
        
        # Step 8: Remove weeks
        week_deleted, _ = weeks.delete()
        self.stdout.write(f"  Removed {week_deleted} weeks")
        
        # Step 9: Remove sub golfers that are no longer used
        self.remove_unused_sub_golfers()
        
        self.stdout.write(self.style.SUCCESS(f"Undo completed successfully for weeks {start_week}-{end_week}!")) 