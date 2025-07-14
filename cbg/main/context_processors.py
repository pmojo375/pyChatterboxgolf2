from main.models import Week, Season
from django.db.models import Q

def weeks_context(request):
    """Context processor to make weeks and golfers available to all templates"""
    try:
        # Get the current season
        current_season = Season.objects.latest('year')
        
        # Get all weeks for the current season that have been fully entered
        # A week is considered "fully entered" if it has golfer matchups
        from main.models import GolferMatchup
        
        # Get weeks that have golfer matchups
        weeks_with_matchups = Week.objects.filter(
            season=current_season,
            rained_out=False
        ).filter(
            id__in=GolferMatchup.objects.filter(week__season=current_season).values_list('week_id', flat=True)
        ).order_by('number')
        
        # Get all golfers for the current season (main league golfers only)
        from main.models import Golfer
        golfer_list = Golfer.objects.filter(team__season=current_season).order_by('name')
        
        # Get all golfers who have subbed in the current season
        sub_golfer_list = Golfer.objects.filter(
            sub__week__season=current_season
        ).distinct().order_by('name')
        
        return {
            'available_weeks': weeks_with_matchups,
            'current_season': current_season,
            'golfer_list': golfer_list,
            'sub_golfer_list': sub_golfer_list,
        }
    except Season.DoesNotExist:
        # No season exists, so no golfers to show
        golfer_list = []
        
        return {
            'available_weeks': [],
            'current_season': None,
            'golfer_list': golfer_list,
            'sub_golfer_list': [],
        } 