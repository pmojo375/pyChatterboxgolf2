from django.db import migrations
from django.utils import timezone
import pytz

def make_datetimes_timezone_aware(apps, schema_editor):
    Week = apps.get_model('main', 'Week')
    eastern = pytz.timezone('US/Eastern')

    for week in Week.objects.all():
        if week.date.tzinfo is None:
            # Convert naive datetime to Eastern Time
            week.date = eastern.localize(week.date)
            week.save(update_fields=['date'])

class Migration(migrations.Migration):

    dependencies = [
        ('main', '0012_auto_20240803_1420'),
    ]

    operations = [

        migrations.RunPython(make_datetimes_timezone_aware),
    ]
