# Golfer–League M2M; backfill existing golfers onto Chatterbox.

from django.db import migrations, models


def assign_chatterbox_league(apps, schema_editor):
    Golfer = apps.get_model('main', 'Golfer')
    League = apps.get_model('main', 'League')
    Through = Golfer.leagues.through
    chatterbox = (
        League.objects.filter(slug='chatterbox-golf').first()
        or League.objects.filter(name__iexact='Chatterbox Golf').first()
        or League.objects.filter(name__icontains='Chatterbox').order_by('pk').first()
        or League.objects.order_by('pk').first()
    )
    if chatterbox is None:
        return
    lid = chatterbox.pk
    for gid in Golfer.objects.values_list('pk', flat=True):
        Through.objects.get_or_create(golfer_id=gid, league_id=lid)


def clear_golfer_leagues(apps, schema_editor):
    Golfer = apps.get_model('main', 'Golfer')
    Through = Golfer.leagues.through
    Through.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0004_season_id_pk'),
    ]

    operations = [
        migrations.AddField(
            model_name='golfer',
            name='leagues',
            field=models.ManyToManyField(
                blank=True,
                related_name='golfers',
                to='main.league',
            ),
        ),
        migrations.RunPython(assign_chatterbox_league, clear_golfer_leagues),
    ]
