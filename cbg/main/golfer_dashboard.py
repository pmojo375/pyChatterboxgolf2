"""Personalized home-page context for logged-in team golfers."""

import re

from django.db.models import Avg, Sum

from main.models import Golfer, GolferMatchup, Handicap, Matchup, Round, Sub, Team


def golfer_on_season_team(golfer, season):
    """True when the golfer is a team member for this season (not sub-only)."""
    return Team.objects.filter(season=season, golfers=golfer).exists()


def _team_rank(standings, golfer_name, teammate_name):
    if not standings or not teammate_name:
        return None
    pair = {golfer_name, teammate_name}
    for rank, row in enumerate(standings, start=1):
        if {row['golfer1'], row['golfer2']} == pair:
            return rank
    return None


def _match_result(golfer_round, opponent_round):
    if not opponent_round:
        return None
    net_diff = (golfer_round.net or 0) - (opponent_round.net or 0)
    if net_diff < 0:
        return 'Win'
    if net_diff > 0:
        return 'Loss'
    return 'Tie'


def _schedule_entry_name(raw_name):
    """Strip sub annotation from schedule display names."""
    if not raw_name:
        return ''
    return re.split(r'\s*\(sub for\b', raw_name, maxsplit=1)[0].strip()


def _subbing_for_from_display(display_name):
    match = re.search(r'\(sub for (.+?)\)', display_name or '')
    return match.group(1) if match else None


def _hcp_for_week(golfer, week):
    try:
        return Handicap.objects.get(golfer=golfer, week=week).handicap
    except Handicap.DoesNotExist:
        latest = (
            Handicap.objects.filter(
                golfer=golfer,
                week__season=week.season,
                week__number__lt=week.number,
            )
            .order_by('-week__number')
            .first()
        )
        return latest.handicap if latest else 0


def _strokes_summary(golfer_hcp, opponent_hcp):
    from main.helper import conventional_round

    golfer_rounded = conventional_round(golfer_hcp)
    opponent_rounded = conventional_round(opponent_hcp)
    if golfer_rounded > opponent_rounded:
        count = golfer_rounded - opponent_rounded
        return {
            'strokes_count': count,
            'strokes_direction': 'getting',
            'strokes_label': f'Getting {count} stroke{"s" if count != 1 else ""}',
            'golfer_hcp': golfer_rounded,
            'opponent_hcp': opponent_rounded,
        }
    if golfer_rounded < opponent_rounded:
        count = opponent_rounded - golfer_rounded
        return {
            'strokes_count': count,
            'strokes_direction': 'giving',
            'strokes_label': f'Giving {count} stroke{"s" if count != 1 else ""}',
            'golfer_hcp': golfer_rounded,
            'opponent_hcp': opponent_rounded,
        }
    return {
        'strokes_count': 0,
        'strokes_direction': 'even',
        'strokes_label': 'Even — no strokes',
        'golfer_hcp': golfer_rounded,
        'opponent_hcp': opponent_rounded,
    }


def _resolve_golfer_by_name(name, season):
    if not name:
        return None
    return (
        Golfer.objects.filter(name=name, team__season=season).first()
        or Golfer.objects.filter(name=name).first()
    )


def _finalize_next_matchup(match_info, playing_golfer, opponent, week):
    if not match_info or match_info.get('no_sub'):
        return match_info
    if playing_golfer and opponent and week:
        match_info.update(
            _strokes_summary(
                _hcp_for_week(playing_golfer, week),
                _hcp_for_week(opponent, week),
            )
        )
    elif match_info.get('_schedule_golfer_hcp') is not None and match_info.get('_schedule_opp_hcp') is not None:
        match_info.update(
            _strokes_summary(
                match_info['_schedule_golfer_hcp'],
                match_info['_schedule_opp_hcp'],
            )
        )
        match_info.pop('_schedule_golfer_hcp', None)
        match_info.pop('_schedule_opp_hcp', None)
    return match_info


def _opponent_from_schedule(golfer, next_week, schedule):
    """Find this golfer's opponent from home-page schedule data."""
    if not schedule:
        return None

    for entry in schedule:
        for key in ('high_match', 'low_match'):
            pair = entry.get(key)
            if not pair or len(pair) != 2:
                continue
            if not pair[0] or not pair[1]:
                continue

            for idx in range(2):
                side = pair[idx][0]
                if not side:
                    continue
                opp_side = pair[1 - idx][0]
                side_hcp = pair[idx][1] if len(pair[idx]) > 1 else None
                opp_hcp = pair[1 - idx][1] if len(pair[1 - idx]) > 1 else None
                if _schedule_entry_name(side) == golfer.name:
                    return {
                        'week_number': next_week.number,
                        'week_date': next_week.date,
                        'opponent_name': _schedule_entry_name(opp_side),
                        'is_playing': True,
                        'subbing_for_name': _subbing_for_from_display(side),
                        '_schedule_golfer_hcp': side_hcp,
                        '_schedule_opp_hcp': opp_hcp,
                    }
                if f'(sub for {golfer.name})' in side:
                    return {
                        'week_number': next_week.number,
                        'week_date': next_week.date,
                        'opponent_name': _schedule_entry_name(opp_side),
                        'is_playing': False,
                        'sub_name': _schedule_entry_name(side),
                        '_schedule_golfer_hcp': side_hcp,
                        '_schedule_opp_hcp': opp_hcp,
                    }
    return None


def _next_matchup_info(golfer, next_week, schedule=None, team=None):
    """Upcoming individual match for next_week, or None if unknown."""
    if not next_week:
        return None

    season = next_week.season

    matchup = (
        GolferMatchup.objects.filter(week=next_week, golfer=golfer)
        .select_related('opponent', 'subbing_for_golfer')
        .first()
    )
    if matchup:
        return _finalize_next_matchup(
            {
                'week_number': next_week.number,
                'week_date': next_week.date,
                'opponent_name': matchup.opponent.name,
                'is_playing': True,
                'subbing_for_name': (
                    matchup.subbing_for_golfer.name
                    if matchup.subbing_for_golfer_id
                    else None
                ),
            },
            matchup.golfer,
            matchup.opponent,
            next_week,
        )

    sub_matchup = (
        GolferMatchup.objects.filter(week=next_week, subbing_for_golfer=golfer)
        .select_related('golfer', 'opponent')
        .first()
    )
    if sub_matchup:
        return _finalize_next_matchup(
            {
                'week_number': next_week.number,
                'week_date': next_week.date,
                'opponent_name': sub_matchup.opponent.name,
                'is_playing': False,
                'sub_name': sub_matchup.golfer.name,
            },
            sub_matchup.golfer,
            sub_matchup.opponent,
            next_week,
        )

    sub_record = (
        Sub.objects.filter(week=next_week, absent_golfer=golfer)
        .select_related('sub_golfer')
        .first()
    )
    if sub_record:
        if sub_record.no_sub:
            return {
                'week_number': next_week.number,
                'week_date': next_week.date,
                'opponent_name': None,
                'is_playing': False,
                'no_sub': True,
            }
        if sub_record.sub_golfer_id:
            scheduled = _opponent_from_schedule(golfer, next_week, schedule)
            sub_match = GolferMatchup.objects.filter(
                week=next_week,
                golfer=sub_record.sub_golfer,
            ).select_related('opponent').first()
            opponent = (
                sub_match.opponent if sub_match
                else _resolve_golfer_by_name(
                    scheduled['opponent_name'] if scheduled else None,
                    season,
                )
            )
            return _finalize_next_matchup(
                {
                    'week_number': next_week.number,
                    'week_date': next_week.date,
                    'opponent_name': (
                        scheduled['opponent_name'] if scheduled
                        else (opponent.name if opponent else None)
                    ),
                    'is_playing': False,
                    'sub_name': sub_record.sub_golfer.name,
                    **(
                        {
                            '_schedule_golfer_hcp': scheduled['_schedule_golfer_hcp'],
                            '_schedule_opp_hcp': scheduled['_schedule_opp_hcp'],
                        }
                        if scheduled and scheduled.get('_schedule_golfer_hcp') is not None
                        else {}
                    ),
                },
                sub_record.sub_golfer,
                opponent,
                next_week,
            )

    scheduled = _opponent_from_schedule(golfer, next_week, schedule)
    if scheduled:
        opponent = _resolve_golfer_by_name(scheduled['opponent_name'], season)
        return _finalize_next_matchup(
            scheduled,
            golfer,
            opponent,
            next_week,
        )

    if team and Matchup.objects.filter(week=next_week, teams=team).exists():
        from main.helper import get_schedule

        team_schedule = get_schedule(next_week)
        scheduled = _opponent_from_schedule(golfer, next_week, team_schedule)
        if scheduled:
            opponent = _resolve_golfer_by_name(scheduled['opponent_name'], season)
            return _finalize_next_matchup(
                scheduled,
                golfer,
                opponent,
                next_week,
            )

    return None


def build_personal_dashboard(
    golfer,
    season,
    *,
    has_second_half_scores,
    first_half_standings,
    second_half_standings,
    full_standings,
    next_week=None,
    next_week_schedule=None,
):
    """
    Build home-page personalization for a golfer in the displayed season.

    Returns None if the golfer is not on a team for this season.
    """
    if not golfer_on_season_team(golfer, season):
        return None

    team = (
        Team.objects.filter(season=season, golfers=golfer)
        .prefetch_related('golfers')
        .first()
    )
    teammate = team.golfers.exclude(pk=golfer.pk).first()
    teammate_name = teammate.name if teammate else None

    rounds = Round.objects.filter(
        golfer=golfer,
        week__season=season,
        week__rained_out=False,
    )
    round_count = rounds.count()

    stats = {
        'rounds_played': round_count,
        'avg_gross': None,
        'avg_net': None,
        'avg_points': None,
        'total_points': None,
        'current_handicap': None,
        'wins': 0,
        'losses': 0,
        'ties': 0,
    }

    if round_count:
        aggregates = rounds.aggregate(
            avg_gross=Avg('gross'),
            avg_net=Avg('net'),
            avg_points=Avg('total_points'),
            total_points=Sum('total_points'),
        )
        stats['avg_gross'] = round(aggregates['avg_gross'], 1)
        stats['avg_net'] = round(aggregates['avg_net'], 1)
        stats['avg_points'] = round(aggregates['avg_points'], 1)
        stats['total_points'] = round(aggregates['total_points'], 1)

        latest_hcp = (
            Handicap.objects.filter(golfer=golfer, week__season=season)
            .order_by('-week__number')
            .first()
        )
        if latest_hcp:
            stats['current_handicap'] = float(latest_hcp.handicap)

        played_rounds = rounds.select_related(
            'week', 'golfer_matchup', 'golfer_matchup__opponent'
        ).order_by('week__number')
        for golfer_round in played_rounds:
            if not golfer_round.golfer_matchup_id:
                continue
            opponent_round = Round.objects.filter(
                golfer=golfer_round.golfer_matchup.opponent,
                week=golfer_round.week,
            ).first()
            result = _match_result(golfer_round, opponent_round)
            if result == 'Win':
                stats['wins'] += 1
            elif result == 'Loss':
                stats['losses'] += 1
            elif result == 'Tie':
                stats['ties'] += 1

    last_round = None
    last_round_obj = (
        rounds.select_related(
            'week',
            'golfer_matchup',
            'golfer_matchup__opponent',
            'subbing_for',
            'handicap',
        )
        .order_by('-week__number')
        .first()
    )
    if last_round_obj:
        opponent_name = None
        match_result = None
        if last_round_obj.golfer_matchup_id:
            opponent_name = last_round_obj.golfer_matchup.opponent.name
            opponent_round = Round.objects.filter(
                golfer=last_round_obj.golfer_matchup.opponent,
                week=last_round_obj.week,
            ).first()
            match_result = _match_result(last_round_obj, opponent_round)

        last_round = {
            'week_number': last_round_obj.week.number,
            'week_date': last_round_obj.week.date,
            'gross': last_round_obj.gross,
            'net': last_round_obj.net,
            'points': round(last_round_obj.total_points, 1),
            'opponent_name': opponent_name,
            'match_result': match_result,
            'was_sub': last_round_obj.is_sub,
            'subbing_for_name': (
                last_round_obj.subbing_for.name if last_round_obj.subbing_for_id else None
            ),
        }

    first_half_rank = _team_rank(first_half_standings, golfer.name, teammate_name)
    second_half_rank = _team_rank(second_half_standings, golfer.name, teammate_name)
    full_rank = _team_rank(full_standings, golfer.name, teammate_name)

    if has_second_half_scores and full_rank is not None:
        primary_rank = full_rank
        primary_label = 'Full season'
    elif first_half_rank is not None:
        primary_rank = first_half_rank
        primary_label = 'First half'
    else:
        primary_rank = None
        primary_label = None

    next_matchup = _next_matchup_info(
        golfer,
        next_week,
        schedule=next_week_schedule,
        team=team,
    )

    return {
        'golfer': golfer,
        'golfer_name': golfer.name,
        'teammate_name': teammate_name,
        'last_round': last_round,
        'next_matchup': next_matchup,
        'stats': stats,
        'ranks': {
            'first_half': first_half_rank,
            'second_half': second_half_rank,
            'full': full_rank,
            'primary': primary_rank,
            'primary_label': primary_label,
        },
    }


def get_logged_in_golfer(user):
    """Return the Golfer linked to this user, or None."""
    if not user.is_authenticated:
        return None
    try:
        return user.golfer_profile
    except Golfer.DoesNotExist:
        return None
