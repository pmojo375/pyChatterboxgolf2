from django.core.management.base import BaseCommand

from main.helper import calculate_field_averages_for_season, get_current_season
from main.league_scope import resolve_league
from main.models import Season


class Command(BaseCommand):
    help = (
        "Calculate field_avg_points and luck on Round rows "
        "(avg points vs every other golfer who posted scores that week). "
        "Use --season YEAR to run one season, or --all for every season."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--season",
            type=int,
            help="Season year to calculate (scoped by --league / default league).",
        )
        parser.add_argument(
            "--league",
            type=str,
            default=None,
            help="League slug. Defaults to the site default league.",
        )
        parser.add_argument(
            "--all",
            action="store_true",
            dest="all_seasons",
            help="Calculate field averages for all seasons (all leagues).",
        )

    def handle(self, *args, **options):
        season_year = options.get("season")
        all_seasons = options.get("all_seasons")
        league_slug = options.get("league")

        if all_seasons and season_year:
            self.stderr.write(self.style.ERROR("Use either --season or --all, not both."))
            return
        if not all_seasons and not season_year:
            self.stderr.write(self.style.ERROR("Provide --season YEAR or --all."))
            return

        if all_seasons:
            seasons = Season.objects.select_related("league").order_by("league__name", "year")
            if not seasons.exists():
                self.stderr.write(self.style.ERROR("No seasons found."))
                return
        else:
            league = resolve_league(league_slug)
            season = get_current_season(year=season_year, league=league)
            if not season:
                league_label = league.slug if league else "default"
                self.stderr.write(
                    self.style.ERROR(f"Season {season_year} not found for league '{league_label}'.")
                )
                return
            seasons = [season]

        grand_weeks = 0
        grand_rounds = 0
        for season in seasons:
            label = f"{season.league.name} {season.year}"
            self.stdout.write(f"Calculating field averages for {label}...")
            result = calculate_field_averages_for_season(season)
            grand_weeks += result["weeks"]
            grand_rounds += result["rounds"]
            self.stdout.write(
                self.style.SUCCESS(
                    f"  {label}: {result['weeks']} weeks, {result['rounds']} rounds updated"
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. {grand_weeks} weeks, {grand_rounds} rounds updated total."
            )
        )
