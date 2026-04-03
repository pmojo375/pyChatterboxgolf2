"""League-aware redirects for multi-league URL schemes."""

from django.shortcuts import redirect


def redirect_home(league, year=None):
    """Home: prefer /slug/year/ when league and year are known."""
    if league is not None and year is not None:
        return redirect(
            'main_with_league_year',
            league_slug=league.slug,
            year=year,
        )
    if year is not None:
        return redirect('main_with_year', year=year)
    return redirect('main')


def redirect_sub_stats_detail(golfer_id, league, year):
    """Sub-stats detail: prefer league-prefixed URL when possible."""
    if league is not None and year is not None:
        return redirect(
            'sub_stats_detail_with_league_year',
            league_slug=league.slug,
            year=year,
            golfer_id=golfer_id,
        )
    if year is not None:
        return redirect(
            'sub_stats_detail_with_year',
            year=year,
            golfer_id=golfer_id,
        )
    return redirect('sub_stats_detail', golfer_id=golfer_id)
