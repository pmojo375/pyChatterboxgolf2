from main.models import Week, Season
from django.db.models import Q

def weeks_context(request):
    """Context processor to make weeks and golfers available to all templates"""
    try:
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
        
        return {
            'available_weeks': weeks_with_complete_scores,
            'current_season': current_season,
            'season': current_season,  # Alias for templates that expect 'season'
            'golfer_list': golfer_list,
            'sub_golfer_list': sub_golfer_list,
            'current_year': year,  # Only set if year is in URL, not for current season
            'all_seasons': all_seasons,
        }
    except Season.DoesNotExist:
        # No season exists, so no golfers to show
        golfer_list = []
        
        return {
            'available_weeks': [],
            'current_season': None,
            'golfer_list': golfer_list,
            'sub_golfer_list': [],
            'current_year': None,
        } 