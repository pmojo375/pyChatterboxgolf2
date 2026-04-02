from main.models import Week, Season
from main.league_scope import league_and_year_from_path


def weeks_context(request):
    """Provide season and week data to all templates.

    Returns a context dictionary containing:
    - ``available_weeks``: weeks in the selected season with complete scores.
    - ``current_season``/``season``: the active :class:`~main.models.Season`.
    - ``golfer_list``: golfers participating in the current season.
    - ``sub_golfer_list``: golfers who have subbed in the current season.
    - ``current_year``: year parsed from the request path, if present.
    - ``all_seasons``: list of all seasons for selector UIs (scoped to the current league).
    - ``is_current_season``: whether the selected season is the latest for that league.
    - ``is_production_host``: flag for chatterboxgolf.com requests.
    - ``multiple_seasons``: whether multiple seasons exist for the league.
    - ``is_league_manager``: whether the user can manage league settings.
    - ``current_league`` / ``league_slug``: resolved league for URL building.
    """
    try:
        try:
            host = request.get_host().lower()
            is_production_host = host.endswith('chatterboxgolf.com')
        except Exception:
            is_production_host = False

        league, path_year = league_and_year_from_path(request.path)

        if not league:
            raise Season.DoesNotExist

        if path_year is not None:
            try:
                current_season = Season.objects.get(league=league, year=path_year)
            except Season.DoesNotExist:
                current_season = Season.objects.filter(league=league).order_by('-year').first()
        else:
            current_season = Season.objects.filter(league=league).order_by('-year').first()

        latest_season = Season.objects.filter(league=league).order_by('-year').first()
        try:
            is_current_season = (
                latest_season is not None
                and current_season is not None
                and current_season.pk == latest_season.pk
            )
        except Exception:
            is_current_season = False

        from main.models import Score, Golfer

        all_seasons = Season.objects.filter(league=league).order_by('-year')
        multiple_seasons = all_seasons.count() > 1

        if current_season is None:
            is_league_manager = False
            user = getattr(request, 'user', None)
            if user and user.is_authenticated:
                if user.is_superuser:
                    is_league_manager = True
                elif league.managers.filter(pk=user.pk).exists():
                    is_league_manager = True
            return {
                'available_weeks': [],
                'current_season': None,
                'season': None,
                'golfer_list': [],
                'sub_golfer_list': [],
                'current_year': path_year,
                'all_seasons': all_seasons,
                'is_current_season': False,
                'is_production_host': is_production_host,
                'multiple_seasons': multiple_seasons,
                'is_league_manager': is_league_manager,
                'current_league': league,
                'league_slug': league.slug,
            }

        weeks_with_complete_scores = []
        all_weeks = Week.objects.filter(
            season=current_season,
            rained_out=False
        ).order_by('number')

        for week in all_weeks:
            score_count = Score.objects.filter(week=week).count()
            if score_count > 0:
                current_season_obj = latest_season
                if current_season == current_season_obj and score_count < week.num_scores:
                    continue
                weeks_with_complete_scores.append(week)

        golfer_list = Golfer.objects.filter(team__season=current_season).order_by('name')

        sub_golfer_list = Golfer.objects.filter(
            sub__week__season=current_season
        ).distinct().order_by('name')

        is_league_manager = False
        user = getattr(request, 'user', None)
        if user and user.is_authenticated:
            if user.is_superuser:
                is_league_manager = True
            elif current_season.league.managers.filter(pk=user.pk).exists():
                is_league_manager = True

        return {
            'available_weeks': weeks_with_complete_scores,
            'current_season': current_season,
            'season': current_season,
            'golfer_list': golfer_list,
            'sub_golfer_list': sub_golfer_list,
            'current_year': path_year,
            'all_seasons': all_seasons,
            'is_current_season': is_current_season,
            'is_production_host': is_production_host,
            'multiple_seasons': multiple_seasons,
            'is_league_manager': is_league_manager,
            'current_league': league,
            'league_slug': league.slug,
        }
    except Season.DoesNotExist:
        golfer_list = []

        return {
            'available_weeks': [],
            'current_season': None,
            'season': None,
            'golfer_list': golfer_list,
            'sub_golfer_list': [],
            'current_year': None,
            'all_seasons': [],
            'is_current_season': False,
            'is_production_host': False,
            'multiple_seasons': False,
            'is_league_manager': False,
            'current_league': None,
            'league_slug': None,
        }
