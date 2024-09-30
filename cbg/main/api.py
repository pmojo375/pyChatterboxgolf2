from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.db.models import Q
from main.models import GolferMatchup, Matchup
from main.serializers import GolferSerializer

def get_matchup_data(request, matchup_id):
    matchup = get_object_or_404(Matchup, pk=matchup_id)
    week = matchup.week

    # Get golfer matchups for this week and matchup
    golfer_matchups = GolferMatchup.objects.filter(
        week=week).filter(
            Q(golfer__in=matchup.teams.all().values_list('golfers', flat=True)) |
            Q(subbing_for_golfer__in=matchup.teams.all().values_list('golfers', flat=True))
    )


    serialized_data = []
    for golfer_matchup in golfer_matchups:
        serializer = GolferSerializer(golfer_matchup, context={'week': week})
        serialized_data.append(serializer.data)

    # Sort golfers based on is_A (True on top)
    serialized_data.sort(key=lambda x: x['is_A'], reverse=True)

    # Map data for four golfers
    data = {
        'golfer1': serialized_data[0],
        'golfer2': serialized_data[1],
        'golfer3': serialized_data[2],
        'golfer4': serialized_data[3],
    }

    print(data)

    return JsonResponse(data)
