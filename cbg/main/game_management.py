from main.models import *


def get_game_winners(game):
    if GameEntry.objects.filter(winner=True, game=game).exists():
        winners = []
        for winner in GameEntry.objects.filter(winner=True, game=game):
            winners.append(winner.golfer.name)
        
        return winners
    else:
        return None


def get_game(week):
    """Get the game object for a given week

    Parameters
    ----------
    week : Week
        The week object you want to get the game for

    Returns
    -------
    Game
        The game object for the given week
    """

    # get the game object for the week
    if Game.objects.filter(week=week).exists():
        game = Game.objects.get(week=week)
    else:
        game = None

    return game


def get_schedule(week_model):
    """
    Given a week model, return the schedule of matches for that week.

    The schedule is returned as a list of lists, where each inner list represents a match and contains two sublists, one
    for the team with the lower handicap golfers and one for the team with the higher handicap golfers.

    :param week_model: The week model to retrieve the schedule for.
    :type week_model: cbg.main.models.Week
    :return: The schedule of matches for the given week.
    :rtype: List[List[List[str]]]
    """
    # Get all matches for the inputed week
    matches = week_model.matchup_set.all()
    schedule = []
    
    if matches.count() == 0:
        return None
    else:
        # Iterate through the matches and format the information for each match
        for match in matches:
            team1_golfer1 = match.teams.all()[0].golfers.all()[0]
            team1_golfer2 = match.teams.all()[0].golfers.all()[1]
            team2_golfer1 = match.teams.all()[1].golfers.all()[0]
            team2_golfer2 = match.teams.all()[1].golfers.all()[1]

            team1_golfer1_hcp = team1_golfer1.handicap_set.all().order_by('-week__date').first().handicap if team1_golfer1.handicap_set.all().order_by('-week__date').first() else 0
            team1_golfer2_hcp = team1_golfer2.handicap_set.all().order_by('-week__date').first().handicap if team1_golfer2.handicap_set.all().order_by('-week__date').first() else 0
            team2_golfer1_hcp = team2_golfer1.handicap_set.all().order_by('-week__date').first().handicap if team2_golfer1.handicap_set.all().order_by('-week__date').first() else 0
            team2_golfer2_hcp = team2_golfer2.handicap_set.all().order_by('-week__date').first().handicap if team2_golfer2.handicap_set.all().order_by('-week__date').first() else 0

            if team1_golfer1_hcp > team1_golfer2_hcp and team2_golfer1_hcp > team2_golfer2_hcp:
                match_low = [team1_golfer2.name, team2_golfer2.name]
                match_high = [team1_golfer1.name, team2_golfer1.name]
            elif team1_golfer1_hcp < team1_golfer2_hcp and team2_golfer1_hcp < team2_golfer2_hcp:
                match_low = [team1_golfer1.name, team2_golfer1.name]
                match_high = [team1_golfer2.name, team2_golfer2.name]
            elif team1_golfer1_hcp > team1_golfer2_hcp and team2_golfer1_hcp < team2_golfer2_hcp:
                match_low = [team1_golfer2.name, team2_golfer1.name]
                match_high = [team1_golfer1.name, team2_golfer2.name]
            else:
                match_low = [team1_golfer1.name, team2_golfer2.name]
                match_high = [team1_golfer2.name, team2_golfer1.name]

            schedule.append({'low_match': match_low, 'high_match': match_high})

        return schedule


def get_score_string(data, holes):
    rank = data['score'] - holes.get(number=data['hole']).par
    
    # Getting 2 strokes
    if data['handicap'] == -2:
        if rank == -2:
            rankStr = 'getting2-stroke_eagle'
        elif rank == -1:
            rankStr = 'getting2-stroke_birdie'
        elif rank == 0:
            rankStr = 'getting2-stroke_par'
        elif rank == 1:
            rankStr = 'getting2-stroke_bogey'
        else:
            rankStr = 'getting2-stroke_worst'
    # Getting 1 stroke
    elif data['handicap'] == -1:
        if rank == -2:
            rankStr = 'getting-stroke_eagle'
        elif rank == -1:
            rankStr = 'getting-stroke_birdie'
        elif rank == 0:
            rankStr = 'getting-stroke_par'
        elif rank == 1:
            rankStr = 'getting-stroke_bogey'
        else:
            rankStr = 'getting-stroke_worst'
    # Straight up
    else:
        if rank == -2:
            rankStr = 'eagle'
        elif rank == -1:
            rankStr = 'birdie'
        elif rank == 0:
            rankStr = 'par'
        elif rank == 1:
            rankStr = 'bogey'
        else:
            rankStr = 'worst'
    
    return rankStr