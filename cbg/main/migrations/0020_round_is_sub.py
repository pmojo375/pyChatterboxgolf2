# Generated by Django 5.0.3 on 2024-09-26 16:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0019_make_dates_timezone_aware'),
    ]

    operations = [
        migrations.AddField(
            model_name='round',
            name='is_sub',
            field=models.BooleanField(default=False),
        ),
    ]
