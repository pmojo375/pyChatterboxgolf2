# Generated by Django 5.1 on 2025-07-13 16:59

from django.db import migrations, models


def remove_duplicate_skin_entries(apps, schema_editor):
    """Remove duplicate skin entries for the same golfer and week"""
    SkinEntry = apps.get_model('main', 'SkinEntry')
    
    # Get all skin entries
    all_entries = SkinEntry.objects.all()
    
    # Track unique combinations
    seen = set()
    to_delete = []
    
    for entry in all_entries:
        key = (entry.golfer_id, entry.week_id)
        if key in seen:
            to_delete.append(entry.id)
        else:
            seen.add(key)
    
    # Delete duplicates
    if to_delete:
        SkinEntry.objects.filter(id__in=to_delete).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0021_round_subbing_for'),
    ]

    operations = [
        # First remove any existing duplicates
        migrations.RunPython(remove_duplicate_skin_entries, reverse_code=migrations.RunPython.noop),
        
        # Add unique constraint
        migrations.AlterUniqueTogether(
            name='skinentry',
            unique_together={('golfer', 'week')},
        ),
    ]
