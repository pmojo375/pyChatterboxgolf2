from django.core.management.base import BaseCommand
from main.models import Round, Sub

class Command(BaseCommand):
    help = 'Backfill subbing_for field on Round model for sub rounds.'

    def handle(self, *args, **options):
        updated = 0
        for round_obj in Round.objects.filter(is_sub=True, subbing_for__isnull=True):
            sub = Sub.objects.filter(week=round_obj.week, sub_golfer=round_obj.golfer).first()
            if sub:
                round_obj.subbing_for = sub.absent_golfer
                round_obj.save()
                updated += 1
        self.stdout.write(self.style.SUCCESS(f'Updated {updated} sub rounds with subbing_for field.'))
