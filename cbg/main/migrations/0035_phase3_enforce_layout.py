# main/migrations/00XX_phase3_enforce_layout.py
from django.db import migrations, models

def assert_hole_configs_filled(apps, schema_editor):
    Hole = apps.get_model("main", "Hole")
    missing = Hole.objects.filter(config__isnull=True).count()
    if missing:
        raise RuntimeError(f"Phase 3 abort: {missing} Hole rows still have config=NULL")

def dedupe_holes_by_config(apps, schema_editor):
    """
    Collapse duplicates so only one Hole exists per (config_id, number).
    Keep the lowest-pk row whose (par, handicap, handicap9, yards) is the mode.
    (No references to 'season' here.)
    """
    from collections import Counter
    from django.db.models import Count

    Hole = apps.get_model("main", "Hole")

    dup_keys = (
        Hole.objects.values("config_id", "number")
        .annotate(cnt=Count("id"))
        .filter(cnt__gt=1)
    )

    for row in dup_keys:
        cfg_id = row["config_id"]
        num = row["number"]

        # All rows for this (config, number)
        holes = list(Hole.objects.filter(config_id=cfg_id, number=num).order_by("id"))

        # Pick the most common spec tuple
        tuples = [(h.par, h.handicap, h.handicap9, h.yards) for h in holes]
        mode_tuple, _ = Counter(tuples).most_common(1)[0]

        # Keep the first row that matches the mode tuple; normalize if needed
        keep = None
        for h in holes:
            if (h.par, h.handicap, h.handicap9, h.yards) == mode_tuple:
                keep = h
                break
        if keep is None:
            keep = holes[0]
        if (keep.par, keep.handicap, keep.handicap9, keep.yards) != mode_tuple:
            keep.par, keep.handicap, keep.handicap9, keep.yards = mode_tuple
            keep.save(update_fields=["par", "handicap", "handicap9", "yards"])

        # Re-point Scores/Points from duplicates to the surviving hole
        Score = apps.get_model("main", "Score")
        Points = apps.get_model("main", "Points")
        other_ids = [h.pk for h in holes if h.pk != keep.pk]
        if other_ids:
            Score.objects.filter(hole_id__in=other_ids).update(hole_id=keep.pk)
            Points.objects.filter(hole_id__in=other_ids).update(hole_id=keep.pk)

        # Now safe to delete the duplicates
        Hole.objects.filter(pk__in=other_ids).delete()

class Migration(migrations.Migration):

    dependencies = [
        ("main", "0033_backfill_course_configs_fi"),
    ]

    operations = [
        # Safety: configs must be filled before we proceed
        migrations.RunPython(assert_hole_configs_filled, reverse_code=migrations.RunPython.noop),

        # Drop any old unique_together on (season, number)
        migrations.AlterUniqueTogether(
            name="hole",
            unique_together=set(),
        ),

        # Make config non-nullable (Stage 2 populated it)
        migrations.AlterField(
            model_name="hole",
            name="config",
            field=models.ForeignKey(
                to="main.courseconfig",
                on_delete=models.deletion.CASCADE,
                related_name="holes",
                null=False,
                blank=False,
            ),
        ),

        # **Deduplicate BEFORE removing season** (doesn't use season, but order is safe)
        migrations.RunPython(dedupe_holes_by_config, reverse_code=migrations.RunPython.noop),

        # Now remove the legacy FK to Season
        migrations.RemoveField(
            model_name="hole",
            name="season",
        ),

        # Add new uniqueness on (config, number)
        migrations.AddConstraint(
            model_name="hole",
            constraint=models.UniqueConstraint(
                fields=["config", "number"],
                name="uniq_config_number",
            ),
        ),

        # Optional: make Season.course_config safer
        migrations.AlterField(
            model_name="season",
            name="course_config",
            field=models.ForeignKey(
                to="main.courseconfig",
                on_delete=models.deletion.PROTECT,
                null=True,
                blank=True,
            ),
        ),

        # Optional: tidy ordering
        migrations.AlterModelOptions(
            name="hole",
            options={"ordering": ["config", "number"], "verbose_name": "Hole", "verbose_name_plural": "Holes"},
        ),
    ]
