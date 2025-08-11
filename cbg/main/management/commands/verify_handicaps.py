from django.core.management.base import BaseCommand

from main.models import Season, Week, Golfer, Handicap, Score, Team
from django.db.models import Sum
from main.helper import (
    calculate_handicap,
    get_current_season,
    get_nine_par_totals,
    DEFAULT_MEMBER_HCP_RULES,
    DEFAULT_SUB_HCP_RULES,
)


class Command(BaseCommand):
    help = (
        "Verify handicaps by simulating season logic (including pre-establishment backfill) and comparing to stored values. "
        "Does not write to the database."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--season",
            type=int,
            help="Season year to verify. Defaults to current season.",
        )

    def handle(self, *args, **options):
        season_year = options.get("season")
        if season_year:
            try:
                season = Season.objects.get(year=season_year)
            except Season.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"Season {season_year} not found"))
                return
        else:
            season = get_current_season()
            if not season:
                self.stderr.write(self.style.ERROR("No current season found"))
                return

        self.stdout.write(f"Verifying handicaps for season {season.year} (no writes)")

        season_weeks = list(Week.objects.filter(season=season).order_by("number"))
        if not season_weeks:
            self.stdout.write(self.style.WARNING("No weeks found for this season"))
            return

        # Golfers that have any handicap record or any score in this season
        golfer_ids_with_handicap = Handicap.objects.filter(week__season=season).values_list("golfer_id", flat=True).distinct()
        golfer_ids_with_scores = Score.objects.filter(week__season=season).values_list("golfer_id", flat=True).distinct()
        golfer_ids = set(list(golfer_ids_with_handicap) + list(golfer_ids_with_scores))

        golfers = Golfer.objects.filter(id__in=golfer_ids).order_by("name")

        total_compared = 0
        total_missing_db = 0
        mismatches = []

        for golfer in golfers:
            is_full_time = Team.objects.filter(season=season, golfers__id=golfer.id).exists()

            # Determine the golfer's played weeks (by scores) in chronological order
            played_weeks = [
                wk for wk in season_weeks
                if Score.objects.filter(week=wk, golfer=golfer).exists()
            ]

            # Build expected handicaps per week using the same establishment/backfill logic as season processing
            member_rules = DEFAULT_MEMBER_HCP_RULES
            sub_rules = DEFAULT_SUB_HCP_RULES
            rules = member_rules if is_full_time else sub_rules
            establish_after = rules.get("establish_after_n_weeks", 3)
            adjust_factor = rules.get("adjust_factor", 0.8)
            rounding_precision = rules.get("rounding_precision", 5)
            required_holes = rules.get("required_holes", 9)
            max_weeks = rules.get("max_weeks", 10)

            par_totals = get_nine_par_totals(season)

            expected_by_week_id = {}
            played_complete_weeks = []

            # Simulate week-by-week
            for wk in season_weeks:
                # Prior-only value
                prior_only = calculate_handicap(
                    golfer,
                    season,
                    wk,
                    ruleset_member=member_rules,
                    ruleset_sub=sub_rules,
                )

                # Track if played and complete
                if Score.objects.filter(week=wk, golfer=golfer).count() >= required_holes:
                    played_complete_weeks.append(wk)

                if 0 < len(played_complete_weeks) <= establish_after:
                    # Pre-establishment seeded value across played weeks
                    # Use up to max_weeks most recent played weeks
                    recent = sorted(played_complete_weeks, key=lambda w: w.date, reverse=True)[:max_weeks]
                    deltas = []
                    for w_used in recent:
                        total = Score.objects.filter(week=w_used, golfer=golfer).aggregate(total=Sum("score"))['total'] or 0
                        par_for = par_totals['front'] if w_used.is_front else par_totals['back']
                        deltas.append(total - par_for)
                    if deltas:
                        seeded = round((sum(deltas) / len(deltas)) * adjust_factor, rounding_precision)
                        # Apply to all played weeks so far
                        for w_used in played_complete_weeks:
                            expected_by_week_id[w_used.id] = seeded
                    # Non-played weeks simply keep prior-only values
                    expected_by_week_id.setdefault(wk.id, prior_only)
                else:
                    # Established or no plays yet: prior-only for this week
                    expected_by_week_id[wk.id] = prior_only

            # Now compare expected to DB for all weeks that have a DB handicap
            for wk in season_weeks:
                db_hcp_obj = Handicap.objects.filter(golfer=golfer, week=wk).first()
                if not db_hcp_obj:
                    total_missing_db += 1
                    mismatches.append({
                        "golfer": golfer.name,
                        "week": wk.number,
                        "reason": "missing_db_handicap",
                        "stored": None,
                        "computed": None,
                        "full_time": is_full_time,
                    })
                    continue

                expected = expected_by_week_id.get(wk.id)
                if expected is None:
                    # Should not happen since we fill every week; treat as mismatch
                    mismatches.append({
                        "golfer": golfer.name,
                        "week": wk.number,
                        "reason": "no_expected_value",
                        "stored": float(db_hcp_obj.handicap),
                        "computed": None,
                        "full_time": is_full_time,
                    })
                    continue

                stored = db_hcp_obj.handicap
                try:
                    stored_rounded = round(float(stored), 5)
                except Exception:
                    stored_rounded = stored

                if stored_rounded != expected:
                    mismatches.append({
                        "golfer": golfer.name,
                        "week": wk.number,
                        "reason": "value_mismatch",
                        "stored": stored_rounded,
                        "computed": expected,
                        "full_time": is_full_time,
                    })
                else:
                    total_compared += 1

        # Reporting
        if mismatches:
            self.stdout.write(self.style.ERROR("Verification FAILED: mismatches found"))
            for mm in mismatches:
                golfer = mm["golfer"]
                week_no = mm["week"]
                if mm["reason"] == "missing_db_handicap":
                    self.stdout.write(f"- {golfer} week {week_no}: missing DB handicap")
                else:
                    stored = mm["stored"]
                    computed = mm["computed"]
                    role = "member" if mm["full_time"] else "sub"
                    self.stdout.write(
                        f"- {golfer} week {week_no} ({role}): stored={stored} computed={computed}"
                    )
        else:
            self.stdout.write(self.style.SUCCESS("Verification PASSED: all compared handicaps match"))

        # Summary
        self.stdout.write("")
        self.stdout.write("Summary:")
        self.stdout.write(f"  Compared: {total_compared}")
        self.stdout.write(f"  Missing DB handicaps: {total_missing_db}")
        self.stdout.write(f"  Mismatches: {len(mismatches)}")


