from django.core.management.base import BaseCommand
from django.db import transaction, connections
from django.db.models import Q
from main.models import (
    Golfer, Season, Week, Score, Hole, Handicap, Game, GameEntry, 
    SkinEntry, Round, Matchup, Sub, Team, GolferMatchup
)
import sqlite3
from django.utils import timezone
import os


class Command(BaseCommand):
    help = 'Migrate scores from old database to new database with name mapping'

    def add_arguments(self, parser):
        parser.add_argument(
            '--old-db-path',
            type=str,
            default='old.sqlite3',
            help='Path to the old database file (default: old.sqlite3)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually making changes'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Skip confirmation prompts'
        )
        parser.add_argument(
            '--only',
            type=str,
            choices=['golfers', 'scores', 'handicaps', 'teams', 'matchups', 'skins', 'games', 'subs'],
            help='Only migrate this specific model (for debugging)'
        )

    def get_old_db_connection(self, db_path):
        """Get connection to the old database"""
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Old database file not found: {db_path}")
        return sqlite3.connect(db_path)

    def get_name_mapping(self):
        """Define the mapping from old names to new names"""
        return {
            'Dan Mcconomy': 'Dan McConomy',
            'Justin Woodly': 'Justin Woodley', 
            'John Fransen': 'John Frandsen',
            'Al Elliot': 'Allen Elliott'
        }

    def get_golfer(self, name):
        """Get existing golfer (don't create)"""
        golfer = Golfer.objects.filter(name=name).first()
        if not golfer:
            self.stdout.write(f'Warning: Golfer "{name}" not found in database')
        return golfer

    def get_season(self, year):
        """Get existing season (don't create)"""
        season = Season.objects.filter(year=year).first()
        if not season:
            self.stdout.write(f'Warning: Season {year} not found in database')
        return season

    def get_week(self, season, week_number, is_front=True):
        """Get existing week (don't create)"""
        if not season:
            return None
            
        # Find existing week (avoid rained out weeks)
        week = Week.objects.filter(
            season=season, 
            number=week_number,
            is_front=is_front,
            rained_out=False
        ).first()
        
        if not week:
            # Let's see what weeks actually exist for this season
            existing_weeks = Week.objects.filter(
                season=season,
                rained_out=False
            ).values_list('number', 'is_front').order_by('number', 'is_front')
            
            self.stdout.write(f'Warning: Week {week_number} ({"Front" if is_front else "Back"}) not found for season {season.year}')
            self.stdout.write(f'  Available weeks for season {season.year}: {list(existing_weeks)}')
        
        return week



    def migrate_golfers(self, old_conn, name_mapping):
        """Get existing golfers from old database"""
        cursor = old_conn.cursor()
        cursor.execute("SELECT id, name, team, year FROM main_golfer")
        old_golfers = cursor.fetchall()
        
        migrated_golfers = {}
        skipped_golfers = []
        
        for old_id, old_name, team, year in old_golfers:
            # Apply name mapping
            new_name = name_mapping.get(old_name, old_name)
            
            # Get existing golfer in new database
            golfer = self.get_golfer(new_name)
            if golfer:  # Only add to mapping if golfer exists
                migrated_golfers[old_id] = golfer
                self.stdout.write(f'Mapped golfer: "{old_name}" -> "{new_name}" (ID: {old_id} -> {golfer.id})')
            else:
                # Check if this was a name mapping attempt
                if old_name in name_mapping:
                    reason = f'Golfer not found in new database (mapped from "{old_name}" to "{new_name}")'
                else:
                    reason = 'Golfer not found in new database (not in name mappings)'
                
                skipped_golfers.append({
                    'id': old_id,
                    'old_name': old_name,
                    'new_name': new_name,
                    'team': team,
                    'year': year,
                    'reason': reason
                })
        
        # Report skipped golfers
        if skipped_golfers:
            self.stdout.write('')
            self.stdout.write('SKIPPED GOLFERS:')
            for golfer in skipped_golfers:
                self.stdout.write(f'  ID {golfer["id"]}: "{golfer["old_name"]}" -> "{golfer["new_name"]}" (Team {golfer["team"]}, {golfer["year"]}) - {golfer["reason"]}')
            self.stdout.write('')
        
        return migrated_golfers

    def migrate_seasons_and_weeks(self, old_conn):
        """Get existing seasons and weeks"""
        cursor = old_conn.cursor()
        cursor.execute("SELECT DISTINCT year FROM main_golfer ORDER BY year")
        years = [row[0] for row in cursor.fetchall()]
        
        seasons = {}
        for year in years:
            season = self.get_season(year)
            if season:  # Only add to mapping if season exists
                seasons[year] = season
        
        # Get front/back information from matchups
        cursor.execute("SELECT DISTINCT year, week, front FROM main_matchup ORDER BY year, week")
        matchup_data = cursor.fetchall()
        
        # Create a mapping of (year, week) -> is_front
        week_front_mapping = {}
        for year, week_num, is_front in matchup_data:
            week_front_mapping[(year, week_num)] = is_front
        
        # Get all weeks from old database (scores, handicaps, games, skins, subs)
        cursor.execute("""
            SELECT DISTINCT year, week FROM (
                SELECT year, week FROM main_score
                UNION
                SELECT year, week FROM main_handicapreal
                UNION
                SELECT year, week FROM main_gameentry
                UNION
                SELECT year, week FROM main_skinentry
                UNION
                SELECT year, week FROM main_subrecord
            ) ORDER BY year, week
        """)
        week_data = cursor.fetchall()
        
        weeks = {}
        for year, week_num in week_data:
            season = seasons.get(year)
            if season:  # Only get weeks if season exists
                # Check if we have front/back info for this week
                if (year, week_num) in week_front_mapping:
                    is_front = week_front_mapping[(year, week_num)]
                    week = self.get_week(season, week_num, is_front=is_front)
                    if week:
                        weeks[(year, week_num, is_front)] = week
                        self.stdout.write(f'Found week: {year} Week {week_num} ({"Front" if is_front else "Back"})')
                    else:
                        self.stdout.write(f'Warning: Week not found for {year} Week {week_num} ({"Front" if is_front else "Back"})')
                else:
                    # Fallback: try both front and back
                    front_week = self.get_week(season, week_num, is_front=True)
                    back_week = self.get_week(season, week_num, is_front=False)
                    if front_week:
                        weeks[(year, week_num, True)] = front_week
                        self.stdout.write(f'Found week: {year} Week {week_num} (Front)')
                    if back_week:
                        weeks[(year, week_num, False)] = back_week
                        self.stdout.write(f'Found week: {year} Week {week_num} (Back)')
                    
                    if not front_week and not back_week:
                        self.stdout.write(f'Warning: Week not found for {year} Week {week_num} (tried both Front and Back)')
        
        return seasons, weeks

    def get_hole(self, season, hole_number):
        """Get existing hole (don't create)"""
        if not season:
            return None
            
        hole = Hole.objects.filter(
            season=season,
            number=hole_number
        ).first()
        
        if not hole:
            self.stdout.write(f'Warning: Hole {hole_number} not found for season {season.year}')
        
        return hole

    def migrate_scores(self, old_conn, migrated_golfers, weeks, dry_run=False):
        """Migrate scores from old database"""
        cursor = old_conn.cursor()
        cursor.execute("""
            SELECT golfer, hole, score, tookMax, week, year 
            FROM main_score 
            ORDER BY year, week, golfer, hole
        """)
        scores_data = cursor.fetchall()
        
        migrated_count = 0
        skipped_count = 0
        skipped_scores = []
        
        for old_golfer_id, old_hole_num, score_value, took_max, week_num, year in scores_data:
            # Skip if golfer doesn't exist in mapping
            if old_golfer_id not in migrated_golfers:
                skipped_count += 1
                skipped_scores.append({
                    'golfer_id': old_golfer_id,
                    'hole': old_hole_num,
                    'score': score_value,
                    'week': week_num,
                    'year': year,
                    'reason': 'Golfer not in migration mapping'
                })
                continue
            
            golfer = migrated_golfers[old_golfer_id]
            
            # Get week (try to find the correct front/back week)
            week = None
            week_key = None
            
            # Try to find the week with the correct front/back designation
            for (w_year, w_week, is_front), w_obj in weeks.items():
                if w_year == year and w_week == week_num:
                    week = w_obj
                    week_key = (w_year, w_week, is_front)
                    break
            
            if not week:
                self.stdout.write(f'Warning: Week not found for {year} Week {week_num}')
                skipped_count += 1
                skipped_scores.append({
                    'golfer_id': old_golfer_id,
                    'hole': old_hole_num,
                    'score': score_value,
                    'week': week_num,
                    'year': year,
                    'reason': f'Week {week_num} not found for {year}'
                })
                continue
            
            # Map old hole number to new hole number
            new_hole_num = self.map_old_hole_to_new_hole(old_hole_num)
            
            # Get hole from existing database (don't create new ones)
            hole = self.get_hole(week.season, new_hole_num)
            
            if not hole:
                skipped_count += 1
                skipped_scores.append({
                    'golfer_id': old_golfer_id,
                    'hole': old_hole_num,
                    'score': score_value,
                    'week': week_num,
                    'year': year,
                    'reason': f'Hole {new_hole_num} not found for {year}'
                })
                continue
            
            if not dry_run:
                # Check if score already exists
                existing_score = Score.objects.filter(
                    golfer=golfer,
                    week=week,
                    hole=hole
                ).first()
                
                if not existing_score:
                    Score.objects.create(
                        golfer=golfer,
                        week=week,
                        hole=hole,
                        score=score_value
                    )
                    migrated_count += 1
                else:
                    skipped_count += 1
                    skipped_scores.append({
                        'golfer_id': old_golfer_id,
                        'hole': old_hole_num,
                        'score': score_value,
                        'week': week_num,
                        'year': year,
                        'reason': 'Score already exists'
                    })
            else:
                migrated_count += 1
        
        # Report skipped scores summary
        if skipped_scores and not dry_run:
            self.stdout.write('')
            self.stdout.write('SKIPPED SCORES SUMMARY:')
            reasons = {}
            for score in skipped_scores:
                reason = score['reason']
                if reason not in reasons:
                    reasons[reason] = 0
                reasons[reason] += 1
            
            for reason, count in reasons.items():
                self.stdout.write(f'  {reason}: {count} scores')
            self.stdout.write('')
        
        return migrated_count, skipped_count

    def map_old_hole_to_new_hole(self, old_hole_num):
        """Map old hole numbers to new hole numbers"""
        # This mapping should be customized based on your course changes
        # For now, assuming a 1:1 mapping, but you can modify this
        hole_mapping = {
            # Example mappings (adjust these based on your actual course changes):
            # 1: 1,   # Old hole 1 -> New hole 1
            # 2: 2,   # Old hole 2 -> New hole 2
            # 3: 4,   # Old hole 3 -> New hole 4 (if holes were reordered)
            # etc.
        }
        
        # If no specific mapping, assume 1:1
        return hole_mapping.get(old_hole_num, old_hole_num)

    def show_hole_mapping_info(self):
        """Show information about hole mapping"""
        self.stdout.write('Hole Mapping Information:')
        self.stdout.write('  - Old hole numbers from old database will be mapped to new hole numbers')
        self.stdout.write('  - If no mapping is specified, 1:1 mapping is assumed')
        self.stdout.write('  - To customize mapping, edit the map_old_hole_to_new_hole method')
        self.stdout.write('  - Example: old hole 3 -> new hole 4 (if holes were reordered)')
        self.stdout.write('')

    def migrate_handicaps(self, old_conn, migrated_golfers, weeks, dry_run=False):
        """Migrate handicaps from old database"""
        cursor = old_conn.cursor()
        cursor.execute("""
            SELECT golfer, handicap, week, year 
            FROM main_handicapreal 
            ORDER BY year, week, golfer
        """)
        handicaps_data = cursor.fetchall()
        
        migrated_count = 0
        skipped_count = 0
        
        for old_golfer_id, handicap_value, week_num, year in handicaps_data:
            # Skip if golfer doesn't exist in mapping
            if old_golfer_id not in migrated_golfers:
                skipped_count += 1
                continue
            
            golfer = migrated_golfers[old_golfer_id]
            
            # Get week (try to find the correct front/back week)
            week = None
            week_key = None
            
            # Try to find the week with the correct front/back designation
            for (w_year, w_week, is_front), w_obj in weeks.items():
                if w_year == year and w_week == week_num:
                    week = w_obj
                    week_key = (w_year, w_week, is_front)
                    break
            
            if not week:
                self.stdout.write(f'Warning: Week not found for handicap {year} Week {week_num}')
                skipped_count += 1
                continue
            
            if not dry_run:
                # Check if handicap already exists
                existing_handicap = Handicap.objects.filter(
                    golfer=golfer,
                    week=week
                ).first()
                
                if not existing_handicap:
                    Handicap.objects.create(
                        golfer=golfer,
                        week=week,
                        handicap=handicap_value
                    )
                    migrated_count += 1
                else:
                    skipped_count += 1
            else:
                migrated_count += 1
        
        return migrated_count, skipped_count

    def migrate_game_entries(self, old_conn, migrated_golfers, weeks, dry_run=False):
        """Migrate game entries from old database"""
        cursor = old_conn.cursor()
        cursor.execute("""
            SELECT golfer, week, year, won 
            FROM main_gameentry 
            WHERE year IN (2023, 2024)
            ORDER BY year, week, golfer
        """)
        entries_data = cursor.fetchall()
        
        migrated_count = 0
        skipped_count = 0
        
        for old_golfer_id, week_num, year, won in entries_data:
            # Skip if golfer doesn't exist in mapping
            if old_golfer_id not in migrated_golfers:
                skipped_count += 1
                continue
            
            golfer = migrated_golfers[old_golfer_id]
            
            # Get week (try to find the correct front/back week)
            week = None
            week_key = None
            
            # Try to find the week with the correct front/back designation
            for (w_year, w_week, is_front), w_obj in weeks.items():
                if w_year == year and w_week == week_num:
                    week = w_obj
                    week_key = (w_year, w_week, is_front)
                    break
            
            if not week:
                self.stdout.write(f'Warning: Week not found for game entry {year} Week {week_num}')
                skipped_count += 1
                continue
            
            # Get or create a default game for this week
            game, created = Game.objects.get_or_create(
                name=f"Week {week_num} Game",
                defaults={'desc': f'Game for week {week_num}', 'week': week}
            )
            
            if not dry_run:
                # Check if game entry already exists
                existing_entry = GameEntry.objects.filter(
                    golfer=golfer,
                    week=week,
                    game=game
                ).first()
                
                if not existing_entry:
                    GameEntry.objects.create(
                        golfer=golfer,
                        week=week,
                        game=game,
                        winner=won
                    )
                    migrated_count += 1
                else:
                    skipped_count += 1
            else:
                migrated_count += 1
        
        return migrated_count, skipped_count

    def migrate_skin_entries(self, old_conn, migrated_golfers, weeks, dry_run=False):
        """Migrate skin entries from old database"""
        cursor = old_conn.cursor()
        cursor.execute("""
            SELECT golfer, week, year, won 
            FROM main_skinentry 
            WHERE year IN (2023, 2024)
            ORDER BY year, week, golfer
        """)
        entries_data = cursor.fetchall()
        
        migrated_count = 0
        skipped_count = 0
        
        for old_golfer_id, week_num, year, won in entries_data:
            # Skip if golfer doesn't exist in mapping
            if old_golfer_id not in migrated_golfers:
                skipped_count += 1
                continue
            
            golfer = migrated_golfers[old_golfer_id]
            
            # Get week (try to find the correct front/back week)
            week = None
            week_key = None
            
            # Try to find the week with the correct front/back designation
            for (w_year, w_week, is_front), w_obj in weeks.items():
                if w_year == year and w_week == week_num:
                    week = w_obj
                    week_key = (w_year, w_week, is_front)
                    break
            
            if not week:
                self.stdout.write(f'Warning: Week not found for skin entry {year} Week {week_num}')
                skipped_count += 1
                continue
            
            if not dry_run:
                # Check if skin entry already exists
                existing_entry = SkinEntry.objects.filter(
                    golfer=golfer,
                    week=week
                ).first()
                
                if not existing_entry:
                    SkinEntry.objects.create(
                        golfer=golfer,
                        week=week,
                        winner=won
                    )
                    migrated_count += 1
                else:
                    skipped_count += 1
            else:
                migrated_count += 1
        
        return migrated_count, skipped_count

    def migrate_teams(self, old_conn, migrated_golfers, seasons, dry_run=False):
        """Migrate teams from old database"""
        cursor = old_conn.cursor()
        cursor.execute("""
            SELECT DISTINCT team, year 
            FROM main_golfer 
            WHERE year IN (2023, 2024) AND team > 0
            ORDER BY year, team
        """)
        team_data = cursor.fetchall()
        
        migrated_count = 0
        skipped_count = 0
        
        for team_num, year in team_data:
            season = seasons.get(year)
            if not season:
                self.stdout.write(f'Warning: Season not found for {year}')
                skipped_count += 1
                continue
            
            # Get all golfers for this team (exclude team 0/null which are subs)
            cursor.execute("""
                SELECT id FROM main_golfer 
                WHERE team = ? AND year = ? AND team > 0
                ORDER BY id
            """, (team_num, year))
            golfer_ids = [row[0] for row in cursor.fetchall()]
            
            if len(golfer_ids) == 0:
                skipped_count += 1
                continue
            
            # Map to new golfers
            new_golfers = []
            for old_id in golfer_ids:
                if old_id in migrated_golfers:
                    new_golfers.append(migrated_golfers[old_id])
            
            if len(new_golfers) == 0:
                skipped_count += 1
                continue
            
            if not dry_run:
                # Check if team already exists with these golfers
                existing_team = None
                for team in Team.objects.filter(season=season):
                    team_golfers = list(team.golfers.all())
                    if len(team_golfers) == len(new_golfers):
                        if all(golfer in team_golfers for golfer in new_golfers):
                            existing_team = team
                            break
                
                if not existing_team:
                    team = Team.objects.create(season=season)
                    team.golfers.set(new_golfers)
                    migrated_count += 1
                    self.stdout.write(f'Created team: {year} Team {team_num} with {len(new_golfers)} golfers')
                else:
                    skipped_count += 1
            else:
                migrated_count += 1
        
        return migrated_count, skipped_count

    def migrate_matchups(self, old_conn, migrated_golfers, weeks, seasons, dry_run=False):
        """Migrate matchups from old database"""
        cursor = old_conn.cursor()
        cursor.execute("""
            SELECT team1, team2, week, front, year 
            FROM main_matchup 
            WHERE year IN (2023, 2024)
            ORDER BY year, week
        """)
        matchup_data = cursor.fetchall()
        
        migrated_count = 0
        skipped_count = 0
        
        for team1_num, team2_num, week_num, is_front, year in matchup_data:
            season = seasons.get(year)
            if not season:
                self.stdout.write(f'Warning: Season not found for matchup {year} Week {week_num}')
                skipped_count += 1
                continue
            
            # Get week
            week_key = (year, week_num, is_front)
            if week_key not in weeks:
                self.stdout.write(f'Warning: Week not found for matchup {year} Week {week_num}')
                skipped_count += 1
                continue
            
            week = weeks[week_key]
            
            # Find teams by their golfers
            team1_golfers = self.get_team_golfers(old_conn, team1_num, year, migrated_golfers)
            team2_golfers = self.get_team_golfers(old_conn, team2_num, year, migrated_golfers)
            
            if not team1_golfers or not team2_golfers:
                self.stdout.write(f'Warning: Could not find golfers for teams {team1_num} and {team2_num}')
                skipped_count += 1
                continue
            
            if not dry_run:
                # Find existing teams
                team1 = self.find_team_by_golfers(season, team1_golfers)
                team2 = self.find_team_by_golfers(season, team2_golfers)
                
                if not team1 or not team2:
                    self.stdout.write(f'Warning: Could not find teams for matchup {year} Week {week_num}')
                    skipped_count += 1
                    continue
                
                # Check if matchup already exists
                existing_matchup = Matchup.objects.filter(
                    week=week,
                    teams=team1
                ).filter(teams=team2).first()
                
                if not existing_matchup:
                    matchup = Matchup.objects.create(week=week)
                    matchup.teams.add(team1, team2)
                    migrated_count += 1
                    self.stdout.write(f'Created matchup: {year} Week {week_num} Team {team1_num} vs Team {team2_num}')
                else:
                    skipped_count += 1
            else:
                migrated_count += 1
        
        return migrated_count, skipped_count

    def get_team_golfers(self, old_conn, team_num, year, migrated_golfers):
        """Get golfers for a specific team"""
        cursor = old_conn.cursor()
        cursor.execute("""
            SELECT id FROM main_golfer 
            WHERE team = ? AND year = ?
            ORDER BY id
        """, (team_num, year))
        golfer_ids = [row[0] for row in cursor.fetchall()]
        
        new_golfers = []
        for old_id in golfer_ids:
            if old_id in migrated_golfers:
                new_golfers.append(migrated_golfers[old_id])
        
        return new_golfers

    def find_team_by_golfers(self, season, golfers):
        """Find existing team by its golfers"""
        for team in Team.objects.filter(season=season):
            team_golfers = list(team.golfers.all())
            if len(team_golfers) == len(golfers):
                if all(golfer in team_golfers for golfer in golfers):
                    return team
        return None

    def migrate_sub_records(self, old_conn, migrated_golfers, weeks, dry_run=False):
        """Migrate sub records from old database"""
        cursor = old_conn.cursor()
        cursor.execute("""
            SELECT week, absent_id, sub_id, year 
            FROM main_subrecord 
            WHERE year IN (2023, 2024)
            ORDER BY year, week
        """)
        sub_data = cursor.fetchall()
        
        migrated_count = 0
        skipped_count = 0
        
        for week_num, absent_id, sub_id, year in sub_data:
            # Skip if golfers don't exist in mapping
            if absent_id not in migrated_golfers:
                skipped_count += 1
                continue
            
            absent_golfer = migrated_golfers[absent_id]
            sub_golfer = None
            
            if sub_id and sub_id in migrated_golfers:
                sub_golfer = migrated_golfers[sub_id]
            
            # Get week (try to find the correct front/back week)
            week = None
            week_key = None
            
            # Try to find the week with the correct front/back designation
            for (w_year, w_week, is_front), w_obj in weeks.items():
                if w_year == year and w_week == week_num:
                    week = w_obj
                    week_key = (w_year, w_week, is_front)
                    break
            
            if not week:
                self.stdout.write(f'Warning: Week not found for sub record {year} Week {week_num}')
                skipped_count += 1
                continue
            
            if not dry_run:
                # Check if sub record already exists
                existing_sub = Sub.objects.filter(
                    week=week,
                    absent_golfer=absent_golfer
                ).first()
                
                if not existing_sub:
                    Sub.objects.create(
                        week=week,
                        absent_golfer=absent_golfer,
                        sub_golfer=sub_golfer,
                        no_sub=(sub_golfer is None)
                    )
                    migrated_count += 1
                    self.stdout.write(f'Created sub record: {year} Week {week_num} {absent_golfer.name} -> {sub_golfer.name if sub_golfer else "No sub"}')
                else:
                    skipped_count += 1
            else:
                migrated_count += 1
        
        return migrated_count, skipped_count

    def handle(self, *args, **options):
        old_db_path = options['old_db_path']
        dry_run = options['dry_run']
        force = options['force']
        only_model = options['only']

        self.stdout.write(
            self.style.SUCCESS(f'Starting migration from old database: {old_db_path}')
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN - No changes will be made')
            )

        if only_model:
            self.stdout.write(
                self.style.WARNING(f'Only migrating: {only_model}')
            )

        # Get name mapping
        name_mapping = self.get_name_mapping()
        self.stdout.write('Name mappings:')
        for old_name, new_name in name_mapping.items():
            self.stdout.write(f'  "{old_name}" -> "{new_name}"')
        self.stdout.write('')

        # Show hole mapping info
        self.show_hole_mapping_info()

        if not force and not dry_run:
            confirm = input('Are you sure you want to proceed with the migration? (yes/no): ')
            if confirm.lower() != 'yes':
                self.stdout.write('Migration cancelled.')
                return

        try:
            # Connect to old database
            old_conn = self.get_old_db_connection(old_db_path)
            
            with transaction.atomic():
                # Always get existing golfers, seasons, weeks, and holes first (they're dependencies)
                if not only_model or only_model in ['golfers', 'scores', 'handicaps', 'teams', 'matchups', 'skins', 'games', 'subs']:
                    self.stdout.write('Getting existing golfers...')
                    migrated_golfers = self.migrate_golfers(old_conn, name_mapping)
                    self.stdout.write(f'Found {len(migrated_golfers)} golfers')
                    self.stdout.write('')

                if not only_model or only_model in ['scores', 'handicaps', 'teams', 'matchups', 'skins', 'games', 'subs']:
                    self.stdout.write('Getting existing seasons and weeks...')
                    seasons, weeks = self.migrate_seasons_and_weeks(old_conn)
                    self.stdout.write(f'Found {len(seasons)} seasons and {len(weeks)} weeks')
                    self.stdout.write('')

                # Initialize counters
                scores_migrated = scores_skipped = 0
                handicaps_migrated = handicaps_skipped = 0
                games_migrated = games_skipped = 0
                skins_migrated = skins_skipped = 0
                teams_migrated = teams_skipped = 0
                matchups_migrated = matchups_skipped = 0
                subs_migrated = subs_skipped = 0

                # Migrate specific models based on --only option
                if not only_model or only_model == 'scores':
                    self.stdout.write('Migrating scores...')
                    scores_migrated, scores_skipped = self.migrate_scores(
                        old_conn, migrated_golfers, weeks, dry_run
                    )
                    self.stdout.write(f'Scores: {scores_migrated} migrated, {scores_skipped} skipped')
                    self.stdout.write('')

                if not only_model or only_model == 'handicaps':
                    self.stdout.write('Migrating handicaps...')
                    handicaps_migrated, handicaps_skipped = self.migrate_handicaps(
                        old_conn, migrated_golfers, weeks, dry_run
                    )
                    self.stdout.write(f'Handicaps: {handicaps_migrated} migrated, {handicaps_skipped} skipped')
                    self.stdout.write('')

                if not only_model or only_model == 'games':
                    self.stdout.write('Migrating game entries...')
                    games_migrated, games_skipped = self.migrate_game_entries(
                        old_conn, migrated_golfers, weeks, dry_run
                    )
                    self.stdout.write(f'Game entries: {games_migrated} migrated, {games_skipped} skipped')
                    self.stdout.write('')

                if not only_model or only_model == 'skins':
                    self.stdout.write('Migrating skin entries...')
                    skins_migrated, skins_skipped = self.migrate_skin_entries(
                        old_conn, migrated_golfers, weeks, dry_run
                    )
                    self.stdout.write(f'Skin entries: {skins_migrated} migrated, {skins_skipped} skipped')
                    self.stdout.write('')

                if not only_model or only_model == 'teams':
                    self.stdout.write('Migrating teams...')
                    teams_migrated, teams_skipped = self.migrate_teams(
                        old_conn, migrated_golfers, seasons, dry_run
                    )
                    self.stdout.write(f'Teams: {teams_migrated} migrated, {teams_skipped} skipped')
                    self.stdout.write('')

                if not only_model or only_model == 'matchups':
                    self.stdout.write('Migrating matchups...')
                    matchups_migrated, matchups_skipped = self.migrate_matchups(
                        old_conn, migrated_golfers, weeks, seasons, dry_run
                    )
                    self.stdout.write(f'Matchups: {matchups_migrated} migrated, {matchups_skipped} skipped')
                    self.stdout.write('')

                if not only_model or only_model == 'subs':
                    self.stdout.write('Migrating sub records...')
                    subs_migrated, subs_skipped = self.migrate_sub_records(
                        old_conn, migrated_golfers, weeks, dry_run
                    )
                    self.stdout.write(f'Sub records: {subs_migrated} migrated, {subs_skipped} skipped')
                    self.stdout.write('')

            old_conn.close()

            total_migrated = (scores_migrated + handicaps_migrated + games_migrated + 
                            skins_migrated + teams_migrated + matchups_migrated + subs_migrated)
            total_skipped = (scores_skipped + handicaps_skipped + games_skipped + 
                           skins_skipped + teams_skipped + matchups_skipped + subs_skipped)

            self.stdout.write(
                self.style.SUCCESS('Migration completed!')
            )
            self.stdout.write(f'Total records migrated: {total_migrated}')
            self.stdout.write(f'Total records skipped: {total_skipped}')

            if dry_run:
                self.stdout.write(
                    self.style.WARNING('This was a dry run. No changes were made.')
                )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error during migration: {e}')
            )
            if not dry_run:
                self.stdout.write('Rolling back changes...')
            return 