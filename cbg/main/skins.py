from main.models import SkinEntry, Hole, Score

def calculate_skin_winners(week):
    """
    Automatically calculate skin winners based on gross scores.
    A skin is won when a golfer has the best gross score on a hole alone.
    """
    # Get all golfers in skins for this week
    skin_entries = SkinEntry.objects.filter(week=week)
    if not skin_entries.exists():
        return []

    # Get the holes for this week (front 9 or back 9)
    if week.is_front:
        holes = Hole.objects.filter(config=week.season.course_config, number__in=range(1, 10))
    else:
        holes = Hole.objects.filter(config=week.season.course_config, number__in=range(10, 19))

    # Dictionary to group skins by golfer
    golfer_skins = {}

    # Check each hole for skin winners
    for hole in holes:
        # Get all scores for this hole from golfers in skins
        scores = []
        for skin_entry in skin_entries:
            score_obj = Score.objects.filter(
                golfer=skin_entry.golfer,
                week=week,
                hole=hole
            ).first()
            if score_obj:
                scores.append((skin_entry.golfer, score_obj.score))

        if scores:
            # Find the best score
            best_score = min(scores, key=lambda x: x[1])[1]

            # Count how many golfers have the best score
            best_score_golfers = [golfer for golfer, score in scores if score == best_score]

            # If only one golfer has the best score, they win the skin
            if len(best_score_golfers) == 1:
                winner = best_score_golfers[0]
                if winner not in golfer_skins:
                    golfer_skins[winner] = []
                golfer_skins[winner].append({
                    'hole': hole.number,
                    'score': best_score
                })

    # Convert to list format for template compatibility
    skin_winners = []
    for golfer, skins in golfer_skins.items():
        for skin in skins:
            skin_winners.append({
                'golfer': golfer,
                'hole': skin['hole'],
                'score': skin['score']
            })

    return skin_winners
