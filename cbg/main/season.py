from main.models import Week, Team, Matchup
from django.db import transaction
from datetime import timedelta


def create_weeks(season, weeks, start_date):
    """
    Create a specified number of weeks for a given season, starting from a specified date.

    Args:
        season (Season): The season object for which the weeks are being created.
        weeks (int): The number of weeks to create.
        start_date (datetime): The starting date for the weeks (should be timezone-aware).

    Returns:
        int: The total number of weeks created.
    """
    # Assume start_date is timezone-aware
    for i in range(1, weeks + 1):
        week_date = start_date + timedelta(weeks=i-1)
        is_front = (i % 2 != 0)
        week = Week(season=season, number=i, date=week_date, is_front=is_front, rained_out=False)
        week.save()
    return weeks

def rain_out_update(week):
    """
    Mark a week as rained out (or undo), shift subsequent week numbers, and maintain
    the calendar's front/back rotation based on dates.

    - When marking as rained out: compress subsequent weeks by one number (no side flip),
      then append a new week at the end with the alternating side.
    - When un-marking: expand subsequent weeks by one number (no side flip),
      then remove the final week to restore the original count.

    This ensures that if week X was Front and gets rained out, the new week X (the
    next calendar week) will be Back, since its side was already scheduled that way.
    """

    if week.rained_out is False:
        with transaction.atomic():
            season = week.season
            all_weeks = list(Week.objects.filter(season=season).order_by('date'))
            # Index of selected week
            idx_map = {w.id: i for i, w in enumerate(all_weeks)}
            k = idx_map[week.id]

            original_side = week.is_front

            # Build proper chain: rained-out week -> first future; each future -> next future; last -> appended (later)
            future_weeks = all_weeks[k + 1:]
            shift_sources = [week] + future_weeks
            # targets will be next future weeks plus appended placeholder

            # 2) Mark week as rained out
            week.rained_out = True
            week.save()

            # 3) Compress numbers for future weeks (shift down by 1)
            for fw in future_weeks:
                fw.number = fw.number - 1
                fw.save()

            # 4) Set sides deterministically: first future = opposite of original, then alternate
            next_side = not original_side
            for fw in future_weeks:
                fw.is_front = next_side
                fw.save()
                next_side = not next_side

            # 5) Create appended new final week with alternating side
            last_by_date = all_weeks[-1]
            appended = Week(
                season=season,
                number=(Week.objects.filter(season=season, rained_out=False).order_by('-number').first().number + 1)
                        if Week.objects.filter(season=season, rained_out=False).exists() else 1,
                date=last_by_date.date + timedelta(weeks=1),
                is_front=next_side,  # continue alternation
                rained_out=False,
            )
            appended.save()

            # 6) Complete matchup shift by mapping sources to targets (last future -> appended)
            shift_targets = future_weeks + [appended]
            # Move from end to start to avoid cascading re-moves
            for i in range(len(shift_sources) - 1, -1, -1):
                src_wk = shift_sources[i]
                dst_wk = shift_targets[i]
                for mu in list(Matchup.objects.filter(week=src_wk)):
                    mu.week = dst_wk
                    mu.save()
    else:
        with transaction.atomic():
            season = week.season
            all_weeks = list(Week.objects.filter(season=season).order_by('date'))
            idx_map = {w.id: i for i, w in enumerate(all_weeks)}
            k = idx_map[week.id]

            # Identify appended week as the one with max date
            appended = max(all_weeks, key=lambda w: w.date)

            # 1) Shift matchups backward using reverse order to avoid re-moving
            future_weeks = [w for w in all_weeks if w.date > week.date]
            chain = future_weeks + [appended]
            dests = [week] + future_weeks
            for i in range(len(chain) - 1, -1, -1):
                src_wk = chain[i]
                dst_wk = dests[i]
                for mu in list(Matchup.objects.filter(week=src_wk)):
                    mu.week = dst_wk
                    mu.save()

            # 2) Delete appended week
            appended.delete()

            # Rebuild list after deletion
            all_weeks = list(Week.objects.filter(season=season).order_by('date'))

            # 3) Expand numbers for future weeks (shift up by 1)
            for w in all_weeks:
                if w.date > week.date:
                    w.number = w.number + 1
                    w.save()

            # 4) Restore sides deterministically from week forward: week keeps its side; then alternate
            next_side = not week.is_front
            for w in sorted([w for w in all_weeks if w.date > week.date], key=lambda x: x.date):
                w.is_front = next_side
                w.save()
                next_side = not next_side

            # 5) Unmark the original week as not rained out
            week.rained_out = False
            week.save()

def create_teams(season, golfers):
    """
    Create teams for a given season with a list of golfers.

    Args:
        season (Season): The season object for which the teams are being created.
        golfers (list): A list of golfer objects to create teams with.

    Returns:
        int: The status of the team creation. 1 if successful, 0 if not.

    """
    
    if len(golfers) == 2 and not Team.objects.filter(season=season, golfers__in=golfers).exists() and golfers[0] != golfers[1]:
        team = Team(season=season)
        team.save()
        team.golfers.add(*golfers)
        return 1
    else:
        return 0