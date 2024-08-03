from django.db import migrations
from django.utils import timezone
import pytz

def make_datetimes_timezone_aware(apps, schema_editor):
    Week = apps.get_model('main', 'Week')
    utc = pytz.UTC

    for week in Week.objects.all():
        if week.date.tzinfo is None:
            week.date = utc.localize(week.date)
            week.save(update_fields=['date'])

class Migration(migrations.Migration):

    dependencies = [
        ('main', '0011_alter_week_date'),
    ]

    operations = [
        migrations.RunPython(make_datetimes_timezone_aware),
    ]
