from django.db import migrations, transaction
from collections import defaultdict
from datetime import date

def forwards(apps, schema_editor):
    Course = apps.get_model("main", "Course")
    CourseConfig = apps.get_model("main", "CourseConfig")
    Season = apps.get_model("main", "Season")
    Hole = apps.get_model("main", "Hole")

    with transaction.atomic():
        # 1) Create/lookup a single Course (rename later in Admin if you like)
        course, _ = Course.objects.get_or_create(
            name="Home Course",
            defaults={"city": "", "state": ""},
        )

        # 2) Build hole signatures per season: ordered by hole number
        # signature = tuple of 18 tuples: (par, handicap, handicap9, yards)
        holes_by_season = defaultdict(list)
        for num, par, hcp, hcp9, yards, season_pk in Hole.objects.values_list(
            "number", "par", "handicap", "handicap9", "yards", "season_id"
        ):
            holes_by_season[season_pk].append((num, par, hcp, hcp9, yards))

        # Season years (we only need year boundaries, not Week dates)
        season_years = dict(Season.objects.values_list("pk", "year"))

        # Group seasons by identical scorecard signature
        sig_to_seasons = defaultdict(list)
        for s_pk, rows in holes_by_season.items():
            rows.sort(key=lambda r: r[0])  # by hole number
            sig = tuple((r[1], r[2], r[3], r[4]) for r in rows)  # (par, hcp, hcp9, yards)
            sig_to_seasons[sig].append(s_pk)

        # Turn groups into a sortable list with min/max years
        groups = []
        for sig, season_pks in sig_to_seasons.items():
            years = sorted(season_years.get(pk) for pk in season_pks if season_years.get(pk) is not None)
            if not years:
                continue
            groups.append({
                "sig": sig,
                "season_pks": season_pks,
                "min_year": min(years),
                "max_year": max(years),
            })

        # Sort by first year so windows line up chronologically
        groups.sort(key=lambda g: g["min_year"])

        # 3) Create CourseConfigs with open/closed bounds, then backfill Season/Hole FKs
        created_configs = []
        for idx, g in enumerate(groups):
            is_first = (idx == 0)
            is_last = (idx == len(groups) - 1)

            # Window rules: first group = no start, last group = no end
            eff_start = None if is_first else date(g["min_year"], 1, 1)
            eff_end   = None if is_last  else date(g["max_year"], 12, 31)

            # Friendly name
            if is_last and eff_start:
                name = f"Layout {eff_start.year}+"
            elif eff_start and eff_end:
                name = f"Layout {eff_start.year}-{eff_end.year}"
            elif eff_end and not eff_start:
                name = f"Layout ≤{eff_end.year}"
            else:
                name = f"Layout {g['min_year']}"

            cfg = CourseConfig.objects.create(
                course=course,
                name=name,
                effective_start=eff_start,
                effective_end=eff_end,
            )
            created_configs.append(cfg)

            # Attach all seasons in this group to cfg
            Season.objects.filter(pk__in=g["season_pks"]).update(course_config_id=cfg.id)
            # Backfill all holes in those seasons
            Hole.objects.filter(season_id__in=g["season_pks"]).update(config_id=cfg.id)

        # 4) Edge case: seasons with no holes (unlikely) — assign them by year to nearest window
        if created_configs:
            cfgs = list(CourseConfig.objects.filter(course=course).order_by("effective_start", "effective_end"))
            for s in Season.objects.filter(course_config__isnull=True):
                y = s.year
                chosen = None
                for c in cfgs:
                    start_y = c.effective_start.year if c.effective_start else None
                    end_y   = c.effective_end.year if c.effective_end else None
                    if (start_y is None or y >= start_y) and (end_y is None or y <= end_y):
                        chosen = c
                        break
                if chosen is None:
                    # If it doesn't fall in any window, stick it on the latest config
                    chosen = cfgs[-1]
                s.course_config_id = chosen.id
                s.save(update_fields=["course_config"])

def backwards(apps, schema_editor):
    # Non-destructive rollback: clear the FKs we populated
    Season = apps.get_model("main", "Season")
    Hole = apps.get_model("main", "Hole")
    Season.objects.update(course_config=None)
    Hole.objects.update(config=None)

class Migration(migrations.Migration):
    dependencies = [
        ("main", "0031_course_courseconfig_hole_config_season_course_config"),
    ]
    operations = [
        migrations.RunPython(forwards, backwards),
    ]
