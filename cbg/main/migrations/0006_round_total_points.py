# Generated by Django 5.0 on 2024-03-03 17:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0005_golfermatchup'),
    ]

    operations = [
        migrations.AddField(
            model_name='round',
            name='total_points',
            field=models.FloatField(null=True),
        ),
    ]
