# Modular Helper Functions Structure

This document describes the new modular structure of the helper functions that were previously all contained in `helper.py`.

## Overview

The original `helper.py` file (1155 lines) has been broken down into 7 focused modules for better maintainability and clarity:

## Module Structure

### 1. `week_management.py`
**Purpose**: Functions related to week and season management
- `get_week()` - Gets the week object from current date
- `get_current_season()` - Gets the current season object
- `get_last_week()` - Gets the last played week
- `get_next_week()` - Gets the next week to be played
- `adjust_weeks()` - Adjusts week numbers after rainouts
- `get_earliest_week_without_full_matchups()` - Finds incomplete weeks

### 2. `golfer_management.py`
**Purpose**: Functions related to golfer operations and substitutions
- `get_golfers()` - Gets golfer objects for a season
- `get_sub()` - Gets sub information for absent golfers
- `get_absent_team_from_sub()` - Gets team info from sub golfer
- `golfer_played()` - Checks if golfer played in a week
- `get_playing_golfers_for_week()` - Gets all active golfers for a week

### 3. `game_management.py`
**Purpose**: Functions related to games, schedules, and score formatting
- `get_game_winners()` - Gets winners of a game
- `get_game()` - Gets game object for a week
- `get_schedule()` - Gets match schedule for a week
- `get_score_string()` - Formats score strings for display

### 4. `handicap_management.py`
**Purpose**: Functions related to handicap calculations and management
- `get_hcp()` - Gets golfer's handicap for a week
- `check_hcp()` - Validates handicap calculations
- `calculate_handicap()` - Calculates handicap for golfer/season/week
- `calculate_and_save_handicaps_for_season()` - Batch handicap processing

### 5. `points_management.py`
**Purpose**: Functions related to points calculation and scoring
- `calculate_team_points()` - Calculates total team points
- `get_golfer_points()` - Calculates points for golfer matchup
- `get_standings()` - Gets standings for season/week
- `get_front_holes()` - Gets front 9 holes for season
- `get_back_holes()` - Gets back 9 holes for season

### 6. `round_management.py`
**Purpose**: Functions related to round generation and processing
- `generate_rounds()` - Generates rounds for entire season
- `generate_round()` - Generates round for specific golfer matchup
- `generate_golfer_matchups()` - Creates golfer matchups for week
- `process_week()` - Complete week processing workflow

### 7. `utils.py`
**Purpose**: General utility functions
- `conventional_round()` - Conventional rounding function

## Backward Compatibility

The original `helper.py` file has been updated to import all functions from the new modules, maintaining full backward compatibility. Any existing code that imports from `helper.py` will continue to work without changes.

## Benefits of This Structure

1. **Better Organization**: Related functions are grouped together
2. **Easier Maintenance**: Smaller, focused files are easier to understand and modify
3. **Improved Readability**: Clear separation of concerns
4. **Better Testing**: Individual modules can be tested independently
5. **Reduced Cognitive Load**: Developers can focus on specific areas of functionality

## Usage Examples

### Importing from specific modules:
```python
from main.week_management import get_current_season, get_next_week
from main.handicap_management import calculate_handicap
from main.points_management import get_golfer_points
```

### Importing from helper.py (backward compatible):
```python
from main.helper import get_current_season, calculate_handicap, get_golfer_points
```

## Migration Notes

- All existing imports from `helper.py` will continue to work
- New code should consider importing directly from specific modules for better clarity
- The modular structure makes it easier to add new functions to appropriate modules
- Each module has focused imports, reducing unnecessary dependencies

## File Sizes

- Original `helper.py`: 1155 lines
- New modular structure:
  - `week_management.py`: ~120 lines
  - `golfer_management.py`: ~80 lines
  - `game_management.py`: ~100 lines
  - `handicap_management.py`: ~200 lines
  - `points_management.py`: ~250 lines
  - `round_management.py`: ~350 lines
  - `utils.py`: ~10 lines
  - `helper.py`: ~50 lines (imports only)