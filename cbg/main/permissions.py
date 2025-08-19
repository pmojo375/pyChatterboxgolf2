from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from .models import League, Season
from .helper import get_current_season

def _resolve_league(kwargs):
    # Future: when you add slugged URLs, this kicks in automatically
    if 'league_slug' in kwargs:
        return get_object_or_404(League, slug=kwargs['league_slug'])
    # Today: resolve via an explicit year param if the view has one
    if 'year' in kwargs and kwargs['year'] is not None:
        season = get_object_or_404(Season, year=kwargs['year'])
        return season.league
    # Fallback: current season's league (keeps existing URLs working)
    season = get_current_season()
    if not season or not season.league_id:
        # Safety: only superuser can proceed when we can't determine a league
        return None
    return season.league

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