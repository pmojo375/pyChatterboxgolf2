# Generated by Django 4.1.2 on 2022-10-16 22:25

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Game',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=80)),
                ('desc', models.TextField(max_length=480)),
            ],
        ),
        migrations.CreateModel(
            name='Golfer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=40)),
            ],
        ),
        migrations.CreateModel(
            name='Hole',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('number', models.IntegerField()),
                ('par', models.IntegerField()),
                ('handicap', models.IntegerField()),
                ('handicap9', models.IntegerField()),
                ('yards', models.IntegerField()),
            ],
        ),
        migrations.CreateModel(
            name='Season',
            fields=[
                ('year', models.IntegerField(primary_key=True, serialize=False)),
            ],
        ),
        migrations.CreateModel(
            name='Week',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateTimeField()),
                ('rained_out', models.BooleanField()),
                ('number', models.IntegerField()),
                ('is_front', models.BooleanField()),
                ('season', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='main.season')),
            ],
        ),
        migrations.CreateModel(
            name='Team',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('golfers', models.ManyToManyField(to='main.golfer')),
                ('season', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='main.season')),
            ],
        ),
        migrations.CreateModel(
            name='Sub',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('absent_golfer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='absent', to='main.golfer')),
                ('sub_golfer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='sub', to='main.golfer')),
                ('week', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='main.week')),
            ],
        ),
        migrations.CreateModel(
            name='SkinEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('winner', models.BooleanField(default=False)),
                ('golfer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='main.golfer')),
                ('week', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='main.week')),
            ],
        ),
        migrations.CreateModel(
            name='Score',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('score', models.IntegerField()),
                ('golfer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='main.golfer')),
                ('hole', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='main.hole')),
                ('week', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='main.week')),
            ],
        ),
        migrations.CreateModel(
            name='Matchup',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('teams', models.ManyToManyField(to='main.team')),
                ('week', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='main.week')),
            ],
        ),
        migrations.AddField(
            model_name='hole',
            name='season',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='main.season'),
        ),
        migrations.CreateModel(
            name='Handicap',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('handicap', models.FloatField()),
                ('golfer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='main.golfer')),
                ('week', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='main.week')),
            ],
        ),
        migrations.CreateModel(
            name='GameEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('winner', models.BooleanField(default=False)),
                ('game', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='main.game')),
                ('golfer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='main.golfer')),
                ('week', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='main.week')),
            ],
        ),
    ]
