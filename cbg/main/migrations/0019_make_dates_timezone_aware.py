# Generated by Django 5.1 on 2024-08-23 20:36

from django.db import migrations
from django.utils import timezone

def make_dates_timezone_aware(apps, schema_editor):
    Event = apps.get_model('main', 'Week')
    for event in Event.objects.all():
        if timezone.is_naive(event.date):
            event.date = timezone.make_aware(event.date)
            event.save()


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0018_alter_golfermatchup_subbing_for_golfer'),
    ]

    operations = [
        migrations.RunPython(make_dates_timezone_aware),
    ]
