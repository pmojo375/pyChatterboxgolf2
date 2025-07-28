from django.core.management.base import BaseCommand
from django.db import transaction
from main.models import Week, Season, Team, Sub, RandomDrawnTeam
from main.helper import detect_and_create_random_drawn_teams, clear_random_drawn_teams, generate_golfer_matchups


class Command(BaseCommand):
    help = 'Test the random drawn team functionality'

    def add_arguments(self, parser):
        parser.add_argument('week_number', type=int, help='Week number to test')
        parser.add_argument('--season', type=int, help='Season year (defaults to current season)')
        parser.add_argument('--clear', action='store_true', help='Clear existing random drawn teams first')

    def handle(self, *args, **options):
        week_number = options['week_number']
        season_year = options.get('season')
        
        # Get the season
        if season_year:
            try:
                season = Season.objects.get(year=season_year)
            except Season.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Season {season_year} not found'))
                return
        else:
            season = Season.objects.latest('year')
        
        # Get the week
        try:
            week = Week.objects.get(number=week_number, season=season)
        except Week.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Week {week_number} not found for season {season.year}'))
            return
        
        self.stdout.write(f'Testing random drawn teams for Week {week_number}, Season {season.year}')
        
        # Clear existing random drawn teams if requested
        if options['clear']:
            self.stdout.write('Clearing existing random drawn teams...')
            clear_random_drawn_teams(week)
        
        # Show current subs
        self.stdout.write('\nCurrent subs for this week:')
        subs = Sub.objects.filter(week=week)
        for sub in subs:
            if sub.no_sub:
                self.stdout.write(f'  {sub.absent_golfer.name} - NO SUB')
            else:
                self.stdout.write(f'  {sub.absent_golfer.name} - Sub: {sub.sub_golfer.name}')
        
        # Detect and create random drawn teams
        self.stdout.write('\nDetecting teams where both golfers have no subs...')
        random_drawn_teams = detect_and_create_random_drawn_teams(week)
        
        if random_drawn_teams:
            self.stdout.write('\nRandom drawn teams created:')
            for absent_team, drawn_team in random_drawn_teams.items():
                self.stdout.write(f'  {drawn_team} plays for {absent_team}')
        else:
            self.stdout.write('\nNo teams found where both golfers have no subs')
        
        # Show all random drawn team records
        self.stdout.write('\nAll RandomDrawnTeam records for this week:')
        random_drawn_records = RandomDrawnTeam.objects.filter(week=week)
        for record in random_drawn_records:
            self.stdout.write(f'  {record.drawn_team} plays for {record.absent_team}')
        
        self.stdout.write(self.style.SUCCESS('\nTest completed successfully!'))