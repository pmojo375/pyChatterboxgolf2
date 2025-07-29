from django.core.management.base import BaseCommand
from django.core.management import call_command
import subprocess
import sys
import os
import platform


class Command(BaseCommand):
    help = 'Start Celery worker for the CBG application'

    def add_arguments(self, parser):
        parser.add_argument(
            '--loglevel',
            default='info',
            help='Set the log level (default: info)',
        )
        parser.add_argument(
            '--concurrency',
            default='1',
            help='Number of worker processes (default: 1)',
        )
        parser.add_argument(
            '--queues',
            default='default',
            help='Comma-separated list of queues to consume from (default: default)',
        )
        parser.add_argument(
            '--pool',
            choices=['threads', 'prefork', 'solo'],
            help='Worker pool type (auto-detected on Windows)',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting Celery worker...')
        )
        
        # Build the celery worker command - start simple
        cmd = [
            'celery',
            '-A', 'cbg',
            'worker',
            '--loglevel=' + options['loglevel'],
        ]
        
        # Windows-specific configuration
        if platform.system().lower() == 'windows':
            if not options['pool']:
                options['pool'] = 'solo'
            self.stdout.write(
                self.style.WARNING('Windows detected - using solo pool for better compatibility')
            )
            cmd.extend(['--pool=' + options['pool']])
        elif options['pool']:
            cmd.extend(['--pool=' + options['pool']])
        
        try:
            # Start the celery worker
            self.stdout.write(f"Running command: {' '.join(cmd)}")
            
            # On Windows, use shell=True and join the command as a string
            if platform.system().lower() == 'windows':
                subprocess.run(' '.join(cmd), check=True, shell=True)
            else:
                subprocess.run(cmd, check=True)
                
        except subprocess.CalledProcessError as e:
            self.stdout.write(
                self.style.ERROR(f'Failed to start Celery worker: {e}')
            )
            sys.exit(1)
        except KeyboardInterrupt:
            self.stdout.write(
                self.style.WARNING('Celery worker stopped by user')
            )
        except FileNotFoundError:
            self.stdout.write(
                self.style.ERROR(
                    'Celery command not found. Make sure Celery is installed: pip install celery'
                )
            )
            sys.exit(1) 