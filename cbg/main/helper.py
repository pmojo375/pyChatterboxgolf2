# Import all functions from the new modular files for backward compatibility
from .week_management import (
    get_week,
    get_current_season,
    get_last_week,
    get_next_week,
    adjust_weeks,
    get_earliest_week_without_full_matchups
)

from .golfer_management import (
    get_golfers,
    get_sub,
    get_absent_team_from_sub,
    golfer_played,
    get_playing_golfers_for_week
)

from .game_management import (
    get_game_winners,
    get_game,
    get_schedule,
    get_score_string
)

from .handicap_management import (
    get_hcp,
    check_hcp,
    calculate_handicap,
    calculate_and_save_handicaps_for_season
)

from .points_management import (
    calculate_team_points,
    get_golfer_points,
    get_standings,
    get_front_holes,
    get_back_holes
)

from .round_management import (
    generate_rounds,
    generate_round,
    generate_golfer_matchups,
    process_week
)

from .utils import conventional_round

'''
Need to run the golfer matchup generator weekly. Need to figure out trigger
Need to figure out the handicap trigger for when the scores are posted and when to run a full generate
Need to figure out when to run the generate_rounds function
'''
    
        
    