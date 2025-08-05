from django.core.management.base import BaseCommand
from django.utils import timezone
from main.models import Week
import pytz

class Command(BaseCommand):
    help = 'Set all Week.date values to noon (12:00 PM) Eastern Time on their respective Tuesday.'

    def handle(self, *args, **options):
        eastern = pytz.timezone('America/Detroit')
        updated = 0
        for week in Week.objects.all():
            date = week.date
            # Make sure date is aware and in local time
            if timezone.is_naive(date):
                # Assume naive datetimes are in local time
                date = eastern.localize(date)
            else:
                date = timezone.localtime(date, eastern)
            # Set time to noon
            new_date = date.replace(hour=12, minute=0, second=0, microsecond=0)
            # If not already correct, update
            if new_date != week.date:
                week.date = new_date
                week.save(update_fields=['date'])
                self.stdout.write(f"Updated Week id={week.id}, number={week.number} to {new_date}")
                updated += 1
        self.stdout.write(self.style.SUCCESS(f"Updated {updated} Week.date values to noon Eastern Time."))