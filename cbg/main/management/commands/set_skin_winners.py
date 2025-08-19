from django.core.management.base import BaseCommand
from main.models import Week, SkinEntry
from main.skins import calculate_skin_winners

class Command(BaseCommand):
    help = 'Reset and set SkinEntry.winner for all weeks across all seasons.'

    def handle(self, *args, **options):
        weeks = Week.objects.all().order_by('season__year', 'number')
        total_weeks = weeks.count()
        self.stdout.write(f'Processing {total_weeks} weeks...')
        updated_weeks = 0
        for week in weeks:
            # Reset all winners for this week
            SkinEntry.objects.filter(week=week).update(winner=False)
            # Calculate new winners
            skin_winners = calculate_skin_winners(week)
            for winner in skin_winners:
                golfer = winner['golfer']
                SkinEntry.objects.filter(week=week, golfer=golfer).update(winner=True)
            updated_weeks += 1
            self.stdout.write(f'Processed week {week.number} ({week.season.year})')
        self.stdout.write(self.style.SUCCESS(f'Successfully set skins winners for {updated_weeks} weeks.'))
