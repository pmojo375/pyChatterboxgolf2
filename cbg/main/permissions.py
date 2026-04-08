from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from .models import League, Season
from .helper import get_current_season
from .league_scope import resolve_league as resolve_league_from_slug


def _resolve_league(kwargs):
    slug = kwargs.get('league_slug')
    if slug:
        return get_object_or_404(League, slug=slug)
    year = kwargs.get('year')
    league = resolve_league_from_slug(None)
    if year is not None and league is not None:
        season = Season.objects.filter(league=league, year=year).first()
        if season:
            return season.league
    season = get_current_season(league=league) if league else get_current_season()
    if season and getattr(season, 'league_id', None):
        return season.league
    return league

def league_manager_required(view_func):
    @login_required
    def _wrapped(request, *args, **kwargs):
        league = _resolve_league(kwargs)
        # Always allow superuser (you), otherwise require per-league manager
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        if league is None or not league.managers.filter(pk=request.user.pk).exists():
            raise PermissionDenied
        request.league = league  # handy if you need it in the view
        return view_func(request, *args, **kwargs)
    return _wrapped