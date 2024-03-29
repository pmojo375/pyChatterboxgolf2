# Generated by Django 5.0 on 2024-03-03 16:23

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0004_alter_score_score'),
    ]

    operations = [
        migrations.CreateModel(
            name='GolferMatchup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_A', models.BooleanField(default=False)),
                ('golfer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='main.golfer')),
                ('opponent', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='opponent', to='main.golfer')),
                ('week', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='week', to='main.week')),
            ],
        ),
    ]
