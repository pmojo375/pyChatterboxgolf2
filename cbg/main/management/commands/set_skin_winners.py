from django.core.management.base import BaseCommand
from main.models import Week, SkinEntry
from main.views import calculate_skin_winners

class Command(BaseCommand):
    help = 'Set the winner field for all SkinEntry objects in all weeks and seasons.'

    def handle(self, *args, **options):
        total_updated = 0
        weeks = Week.objects.filter(rained_out=False)
        for week in weeks:
            self.stdout.write(f'Processing week {week}...')
            # Reset all to False first
            SkinEntry.objects.filter(week=week).update(winner=False)
            # Get winners using existing logic
            skin_winners = calculate_skin_winners(week)
            for winner in skin_winners:
                golfer = winner['golfer']
                # Set winner=True for this golfer/week
                updated = SkinEntry.objects.filter(week=week, golfer=golfer).update(winner=True)
                total_updated += updated
        self.stdout.write(self.style.SUCCESS(f'Successfully updated {total_updated} SkinEntry objects.'))
