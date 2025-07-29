from django.core.management.base import BaseCommand
from main.tasks import test_task, process_week_async, generate_matchups_async, calculate_handicaps_async, generate_rounds_async
from main.models import Week, Season


class Command(BaseCommand):
    help = 'Test Celery tasks'

    def add_arguments(self, parser):
        parser.add_argument(
            '--task',
            choices=['test', 'process_week', 'generate_matchups', 'calculate_handicaps', 'generate_rounds'],
            default='test',
            help='Which task to test (default: test)',
        )
        parser.add_argument(
            '--week-id',
            type=int,
            help='Week ID for process_week and generate_matchups tasks',
        )
        parser.add_argument(
            '--season-year',
            type=int,
            help='Season year for calculate_handicaps and generate_rounds tasks',
        )

    def handle(self, *args, **options):
        task_type = options['task']
        
        self.stdout.write(
            self.style.SUCCESS(f'Testing Celery task: {task_type}')
        )
        
        if task_type == 'test':
            # Test the simple test task
            result = test_task.delay()
            self.stdout.write(f'Task ID: {result.id}')
            self.stdout.write('Waiting for result...')
            task_result = result.get(timeout=10)
            self.stdout.write(
                self.style.SUCCESS(f'Task result: {task_result}')
            )
            
        elif task_type == 'process_week':
            if not options['week_id']:
                self.stdout.write(
                    self.style.ERROR('--week-id is required for process_week task')
                )
                return
                
            # Check if week exists
            try:
                week = Week.objects.get(id=options['week_id'])
                self.stdout.write(f'Processing week {week.number}')
            except Week.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Week with ID {options["week_id"]} does not exist')
                )
                return
                
            result = process_week_async.delay(options['week_id'])
            self.stdout.write(f'Task ID: {result.id}')
            self.stdout.write('Waiting for result...')
            task_result = result.get(timeout=30)
            self.stdout.write(
                self.style.SUCCESS(f'Task result: {task_result}')
            )
            
        elif task_type == 'generate_matchups':
            if not options['week_id']:
                self.stdout.write(
                    self.style.ERROR('--week-id is required for generate_matchups task')
                )
                return
                
            # Check if week exists
            try:
                week = Week.objects.get(id=options['week_id'])
                self.stdout.write(f'Generating matchups for week {week.number}')
            except Week.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Week with ID {options["week_id"]} does not exist')
                )
                return
                
            result = generate_matchups_async.delay(options['week_id'])
            self.stdout.write(f'Task ID: {result.id}')
            self.stdout.write('Waiting for result...')
            task_result = result.get(timeout=30)
            self.stdout.write(
                self.style.SUCCESS(f'Task result: {task_result}')
            )
            

            
        elif task_type == 'calculate_handicaps':
            if not options['season_year']:
                self.stdout.write(
                    self.style.ERROR('--season-year is required for calculate_handicaps task')
                )
                return
                
            # Check if season exists
            try:
                season = Season.objects.get(year=options['season_year'])
                self.stdout.write(f'Calculating handicaps for season {season.year}')
            except Season.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Season with year {options["season_year"]} does not exist')
                )
                return
                
            result = calculate_handicaps_async.delay(options['season_year'])
            self.stdout.write(f'Task ID: {result.id}')
            self.stdout.write('Waiting for result...')
            task_result = result.get(timeout=60)
            self.stdout.write(
                self.style.SUCCESS(f'Task result: {task_result}')
            )
            
        elif task_type == 'generate_rounds':
            if not options['season_year']:
                self.stdout.write(
                    self.style.ERROR('--season-year is required for generate_rounds task')
                )
                return
                
            # Check if season exists
            try:
                season = Season.objects.get(year=options['season_year'])
                self.stdout.write(f'Generating rounds for season {season.year}')
                result = generate_rounds_async.delay(options['season_year'])
                self.stdout.write(f'Task ID: {result.id}')
                self.stdout.write('Waiting for result...')
                task_result = result.get(timeout=60)
                self.stdout.write(
                    self.style.SUCCESS(f'Task result: {task_result}')
                )
            except Season.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Season with year {options["season_year"]} does not exist')
                )
                return