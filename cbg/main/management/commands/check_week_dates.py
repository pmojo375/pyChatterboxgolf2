from django.core.management.base import BaseCommand
from django.utils import timezone
from main.models import Week

class Command(BaseCommand):
    help = 'Check if all Week.date values are on a Tuesday (weekday=1)'

    def handle(self, *args, **options):
        # Get all weeks
        weeks = Week.objects.all()
        not_tuesday = []
        for week in weeks:
            date = week.date
            # If USE_TZ is True, ensure date is aware and in local time
            if timezone.is_naive(date):
                self.stdout.write(self.style.WARNING(f"Week id={week.id} has naive datetime: {date}"))
            else:
                date = timezone.localtime(date)
            if date.weekday() != 1:
                not_tuesday.append((week.id, date, week.number))
        if not not_tuesday:
            self.stdout.write(self.style.SUCCESS("All Week.date values are on a Tuesday."))
        else:
            self.stdout.write(self.style.ERROR(f"Weeks not on Tuesday (weekday=1):"))
            for id, date, number in not_tuesday:
                self.stdout.write(f"  Week id={id}, number={number}, date={date} (weekday={date.weekday()})")