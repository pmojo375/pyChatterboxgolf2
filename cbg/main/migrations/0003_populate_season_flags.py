from django.db import migrations


def set_season_play_flags(apps, schema_editor):
    Season = apps.get_model('main', 'Season')
    disabled_years = {2019, 2020}

    for season in Season.objects.all():
        if season.year in disabled_years:
            season.playing_skins = False
            season.playing_games = False
            # No fees when not playing
            season.skins_entry_fee = 0
            season.game_entry_fee = 0
        else:
            season.playing_skins = True
            season.playing_games = True
            season.skins_entry_fee = 5
            season.game_entry_fee = 2
        season.save(update_fields=[
            'playing_skins', 'skins_entry_fee', 'playing_games', 'game_entry_fee'
        ])


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0002_season_game_entry_fee_season_players_per_team_and_more'),
    ]

    operations = [
        migrations.RunPython(set_season_play_flags, migrations.RunPython.noop),
    ]


