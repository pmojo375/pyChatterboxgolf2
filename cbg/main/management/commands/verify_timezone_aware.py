from django.core.management.base import BaseCommand
from main.models import Week

class Command(BaseCommand):
    help = 'Verify timezone awareness of Week dates'

    def handle(self, *args, **kwargs):
        for week in Week.objects.all():
            self.stdout.write(f'Week {week.id}: {week.date} (tzinfo: {week.date.tzinfo})')
