from main.models import Week, Season


def weeks_context(request):
    """Provide season and week data to all templates.

    Returns a context dictionary containing:
    - ``available_weeks``: weeks in the selected season with complete scores.
    - ``current_season``/``season``: the active :class:`~main.models.Season`.
    - ``golfer_list``: golfers participating in the current season.
    - ``sub_golfer_list``: golfers who have subbed in the current season.
    - ``current_year``: year parsed from the request path, if present.
    - ``all_seasons``: list of all seasons for selector UIs.
    - ``is_current_season``: whether the selected season is the latest.
    - ``is_production_host``: flag for chatterboxgolf.com requests.
    - ``multiple_seasons``: whether multiple seasons exist in the system.
    - ``is_league_manager``: whether the user can manage league settings.
    """
    try:
        # Determine if request is coming from the production host
        try:
            host = request.get_host().lower()
            is_production_host = host.endswith('chatterboxgolf.com')
        except Exception:
            is_production_host = False

        # Check if year is in the URL path
        path_parts = request.path.strip('/').split('/')
        year = None
        
        # Look for year in the URL path (e.g., /2024/1 or /2024/)
        if len(path_parts) >= 1 and path_parts[0] and path_parts[0].isdigit() and len(path_parts[0]) == 4:
            # First part is a 4-digit year
            year = int(path_parts[0])
        elif len(path_parts) >= 2 and path_parts[1] and path_parts[1].isdigit() and len(path_parts[1]) == 4:
            # Second part is a 4-digit year (e.g., /stats/2024/123)
            year = int(path_parts[1])
        
        # Get the season for the specified year or current season
        if year:
            try:
                current_season = Season.objects.get(year=year)
            except Season.DoesNotExist:
                # If specified year doesn't exist, fall back to latest season
                current_season = Season.objects.latest('year')
        else:
            # No year specified, use latest season
            current_season = Season.objects.latest('year')
        
        # Determine if the selected season is the current (latest) season
        try:
            latest_season = Season.objects.latest('year')
            is_current_season = (current_season.year == latest_season.year)
        except Season.DoesNotExist:
            is_current_season = False
        
        # Get all weeks for the current season that have been fully entered
        # A week is considered "fully entered" if it has scores
        from main.models import GolferMatchup, Score
        
        # Get weeks that have scores (more flexible for historical seasons)
        weeks_with_complete_scores = []
        all_weeks = Week.objects.filter(
            season=current_season,
            rained_out=False
        ).order_by('number')
        
        for week in all_weeks:
            score_count = Score.objects.filter(week=week).count()
            # For historical seasons, be more flexible - if there are scores, consider it played
            # For current season, be more strict about having all expected scores
            if score_count > 0:
                # If it's the current season, check for complete scores
                current_season_obj = Season.objects.latest('year')
                if current_season == current_season_obj and score_count < week.num_scores:
                    continue
                weeks_with_complete_scores.append(week)
        
        # Get all golfers for the current season (main league golfers only)
        from main.models import Golfer
        golfer_list = Golfer.objects.filter(team__season=current_season).order_by('name')
        
        # Get all golfers who have subbed in the current season
        sub_golfer_list = Golfer.objects.filter(
            sub__week__season=current_season
        ).distinct().order_by('name')
        
        # Get all seasons for the season selector
        all_seasons = Season.objects.all().order_by('-year')
        
        multiple_seasons = Season.objects.count() > 1
        # Determine if user is a league manager or superuser
        is_league_manager = False
        user = getattr(request, 'user', None)
        if user and user.is_authenticated:
            if user.is_superuser:
                is_league_manager = True
            elif hasattr(current_season, 'league') and current_season.league.managers.filter(pk=user.pk).exists():
                is_league_manager = True
        return {
            'available_weeks': weeks_with_complete_scores,
            'current_season': current_season,
            'season': current_season,  # Alias for templates that expect 'season'
            'golfer_list': golfer_list,
            'sub_golfer_list': sub_golfer_list,
            'current_year': year,  # Only set if year is in URL, not for current season
            'all_seasons': all_seasons,
            'is_current_season': is_current_season,
            'is_production_host': is_production_host,
            'multiple_seasons': multiple_seasons,
            'is_league_manager': is_league_manager,
        }
    except Season.DoesNotExist:
        # No season exists, so no golfers to show
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
        }
