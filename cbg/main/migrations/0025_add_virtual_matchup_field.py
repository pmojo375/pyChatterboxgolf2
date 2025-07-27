# Generated manually for adding virtual matchup field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0024_alter_golfermatchup_is_a'),
    ]

    operations = [
        migrations.AddField(
            model_name='golfermatchup',
            name='is_virtual_matchup',
            field=models.BooleanField(default=False, help_text='Flag for virtual matchups using random drawn team'),
        ),
    ]