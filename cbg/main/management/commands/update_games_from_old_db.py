from django.core.management.base import BaseCommand
from django.db import transaction
from main.models import Game, GameEntry, Week, Season
import sqlite3
import os

class Command(BaseCommand):
    help = 'Update 2023 games, create 2024 games, and fix GameEntry links using old DB as source of truth.'

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

    def get_old_db_connection(self, db_path):
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Old database file not found: {db_path}")
        return sqlite3.connect(db_path)

    def handle(self, *args, **options):
        old_db_path = options['old_db_path']
        dry_run = options['dry_run']
        force = options['force']

        self.stdout.write(self.style.SUCCESS(f'Starting update from old database: {old_db_path}'))
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN - No changes will be made'))
        if not force and not dry_run:
            confirm = input('Are you sure you want to proceed with the update? (yes/no): ')
            if confirm.lower() != 'yes':
                self.stdout.write('Update cancelled.')
                return

        try:
            old_conn = self.get_old_db_connection(old_db_path)
            cursor = old_conn.cursor()
            # Read all games for 2023 and 2024 from old DB
            cursor.execute("SELECT id, name, desc, week, year FROM main_game WHERE year IN (2023, 2024)")
            old_games = cursor.fetchall()
            # Build mapping: (year, week) -> (name, desc)
            old_game_map = {(year, week): (name, desc) for (id, name, desc, week, year) in old_games}

            updated_2023 = 0
            created_2024 = 0
            updated_entries = 0
            skipped_entries = 0

            with transaction.atomic():
                # 1. Update 2023 Games
                for (year, week), (name, desc) in old_game_map.items():
                    if year == 2023:
                        # Find the Week object for 2023
                        week_obj = Week.objects.filter(season__year=2023, number=week).first()
                        if not week_obj:
                            self.stdout.write(f'Warning: 2023 week {week} not found in Django DB')
                            continue
                        # Update the Game for this week
                        game = Game.objects.filter(week=week_obj).first()
                        if game:
                            if not dry_run:
                                game.name = name
                                game.desc = desc
                                game.save()
                            updated_2023 += 1
                        else:
                            self.stdout.write(f'Warning: Game for 2023 week {week} not found')
                # 2. Create 2024 Games
                for (year, week), (name, desc) in old_game_map.items():
                    if year == 2024:
                        week_obj = Week.objects.filter(season__year=2024, number=week).first()
                        if not week_obj:
                            self.stdout.write(f'Warning: 2024 week {week} not found in Django DB')
                            continue
                        game, created = Game.objects.get_or_create(
                            week=week_obj,
                            defaults={'name': name, 'desc': desc}
                        )
                        if created:
                            if not dry_run:
                                game.name = name
                                game.desc = desc
                                game.save()
                            created_2024 += 1
                        else:
                            # If already exists, update name/desc if needed
                            if game.name != name or game.desc != desc:
                                if not dry_run:
                                    game.name = name
                                    game.desc = desc
                                    game.save()
                                created_2024 += 1
                # 3. Update GameEntry links
                for entry in GameEntry.objects.all():
                    week_obj = entry.week
                    year = week_obj.season.year
                    week_num = week_obj.number
                    key = (year, week_num)
                    if key in old_game_map:
                        name, desc = old_game_map[key]
                        # Find the correct Game for this week
                        game = Game.objects.filter(week=week_obj, name=name).first()
                        if game and entry.game != game:
                            if not dry_run:
                                entry.game = game
                                entry.save()
                            updated_entries += 1
                        else:
                            skipped_entries += 1
                    else:
                        skipped_entries += 1
            old_conn.close()
            self.stdout.write(self.style.SUCCESS('Update completed!'))
            self.stdout.write(f'2023 Games updated: {updated_2023}')
            self.stdout.write(f'2024 Games created/updated: {created_2024}')
            self.stdout.write(f'GameEntry records updated: {updated_entries}')
            self.stdout.write(f'GameEntry records skipped: {skipped_entries}')
            if dry_run:
                self.stdout.write(self.style.WARNING('This was a dry run. No changes were made.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error during update: {e}'))
            if not dry_run:
                self.stdout.write('Rolling back changes...')
            return
