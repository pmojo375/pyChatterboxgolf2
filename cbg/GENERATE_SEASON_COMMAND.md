# Generate Season Data Command

## Overview
The `generate_season_data` command is a Django management command that generates handicaps, golfer matchups, and rounds for a golf league season. This command is designed to replace the Celery task that was causing deployment crashes.

## Usage

### Basic Usage
```bash
# Generate all data for the current season
python manage.py generate_season_data

# Generate all data for a specific season
python manage.py generate_season_data --season 2025

# Generate data for a specific week
python manage.py generate_season_data --season 2025 --week 4

# Generate data for a range of weeks
python manage.py generate_season_data --season 2025 --week-range 4-9
```

### Options

#### Required Options
- None (uses current season by default)

#### Optional Options
- `--season YEAR`: Specify the season year to process (default: current season)
- `--week NUMBER`: Process only a specific week
- `--week-range "START-END"`: Process a range of weeks (e.g., "4-9")
- `--dry-run`: Show what would be generated without making changes
- `--force`: Force regeneration even if data already exists
- `--skip-handicaps`: Skip handicap generation
- `--skip-matchups`: Skip golfer matchup generation
- `--skip-rounds`: Skip round generation

### Examples

#### Dry Run (Preview)
```bash
# See what would be generated for the current season
python manage.py generate_season_data --dry-run

# See what would be generated for a specific week
python manage.py generate_season_data --season 2025 --week 4 --dry-run
```

#### Force Regeneration
```bash
# Regenerate all data even if it already exists
python manage.py generate_season_data --force

# Regenerate only matchups for a specific week
python manage.py generate_season_data --season 2025 --week 4 --skip-handicaps --skip-rounds --force
```

#### Partial Generation
```bash
# Generate only handicaps
python manage.py generate_season_data --skip-matchups --skip-rounds

# Generate only matchups
python manage.py generate_season_data --skip-handicaps --skip-rounds

# Generate only rounds
python manage.py generate_season_data --skip-handicaps --skip-matchups
```

## What the Command Does

### Step 1: Handicap Generation
- Calls `calculate_and_save_handicaps_for_season()` for the specified season and weeks
- Generates handicaps for all golfers who played in the season
- Handles the complex handicap calculation logic including backdating

### Step 2: Golfer Matchup Generation
- For each week, calls `generate_golfer_matchups(week)`
- Creates `GolferMatchup` objects for all team matchups
- Handles substitutions and the new "no sub" logic
- Preserves A/B status based on original team composition

### Step 3: Round Generation
- For each golfer matchup, calls `generate_round(golfer_matchup)`
- Creates `Round` objects with scores, points, and statistics
- Handles the new points calculation for "no sub" scenarios

## Safety Features

### Duplicate Prevention
- Checks for existing data before generating
- Uses `--force` flag to override existing data
- Implements database transactions for atomicity

### Error Handling
- Continues processing even if individual rounds fail
- Provides detailed error messages
- Uses try-catch blocks to prevent crashes

### Data Integrity
- Verifies that all golfer matchups have corresponding rounds
- Checks for duplicate rounds
- Reports data integrity issues

## Deployment Integration

### Replace Celery Task
Instead of using Celery to run the generation task, you can now use this command:

```bash
# In your deployment script or cron job
python manage.py generate_season_data --season 2025
```

### Cron Job Example
```bash
# Run every hour to check for new data
0 * * * * cd /path/to/your/project && python manage.py generate_season_data --season 2025
```

### Manual Trigger
```bash
# When scores are posted, manually trigger generation
python manage.py generate_season_data --season 2025 --force
```

## Troubleshooting

### Common Issues

1. **No current season found**
   - Create a season or specify a season year with `--season`

2. **No weeks to process**
   - Ensure weeks exist and have scores posted

3. **Permission errors**
   - Ensure the command has write access to the database

4. **Memory issues with large datasets**
   - Process specific weeks or ranges instead of entire season

### Debug Mode
```bash
# Use dry-run to see what would be processed
python manage.py generate_season_data --dry-run

# Check specific week
python manage.py generate_season_data --season 2025 --week 4 --dry-run
```

## Testing

Run the test script to verify the command works:
```bash
cd cbg
python test_generate_season_command.py
```

## Migration from Celery

1. Remove or disable the Celery task that was causing crashes
2. Replace with this command in your deployment process
3. Test with `--dry-run` first
4. Run the command manually to generate existing data
5. Set up automated execution (cron, deployment hook, etc.)

## Performance Considerations

- The command processes weeks sequentially to avoid memory issues
- Uses database transactions for consistency
- Implements proper cleanup to prevent duplicate objects
- Can be run incrementally (week by week) for large datasets 