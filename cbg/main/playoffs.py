from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from django.db.models import Q

from .models import Matchup, Round, Team, Week


@dataclass
class SeedInfo:
    seed: int
    team_id: int
    team_name: str
    source: str  # 'first_half' | 'second_half' | 'half_tie' | 'wildcard'
    points_first_half: float
    points_second_half: float
    points_total: float
    tiebreak_note: Optional[str] = None


def _get_team_name(team: Team) -> str:
    golfers = list(team.golfers.all())
    if len(golfers) >= 2:
        return f"{golfers[0].name} / {golfers[1].name}"
    return str(team)


def _team_points_for_weeks(team: Team, weeks_qs) -> float:
    golfers = list(team.golfers.all())
    if not golfers:
        return 0.0
    golfer_ids = [g.id for g in golfers]

    rounds_qs = Round.objects.filter(week__in=weeks_qs)

    own_points = rounds_qs.filter(golfer__in=golfer_ids, subbing_for__isnull=True).values_list(
        'total_points', flat=True
    )
    sub_points = rounds_qs.filter(subbing_for__in=golfer_ids).values_list('total_points', flat=True)
    return float(sum(own_points) + sum(sub_points))


def _full_points_map(season) -> Tuple[Dict[int, float], Dict[int, float], Dict[int, float]]:
    teams = Team.objects.filter(season=season)
    weeks_first = Week.objects.filter(season=season, number__lte=9, rained_out=False)
    weeks_second = Week.objects.filter(season=season, number__gte=10, rained_out=False)

    first: Dict[int, float] = {}
    second: Dict[int, float] = {}
    total: Dict[int, float] = {}

    for team in teams:
        p1 = _team_points_for_weeks(team, weeks_first)
        p2 = _team_points_for_weeks(team, weeks_second)
        first[team.id] = p1
        second[team.id] = p2
        total[team.id] = p1 + p2

    return first, second, total


def _matchup_weeks_between(team_a: Team, team_b: Team) -> List[int]:
    matchups = (
        Matchup.objects.filter(week__season=team_a.season)
        .filter(teams=team_a)
        .filter(teams=team_b)
        .values_list('week_id', flat=True)
    )
    return list(matchups)


def _team_points_in_specific_weeks(team: Team, week_ids: List[int]) -> float:
    if not week_ids:
        return 0.0
    weeks_qs = Week.objects.filter(id__in=week_ids)
    return _team_points_for_weeks(team, weeks_qs)


def _head_to_head_points(team_a: Team, team_b: Team) -> Tuple[float, float]:
    week_ids = _matchup_weeks_between(team_a, team_b)
    a_points = _team_points_in_specific_weeks(team_a, week_ids)
    b_points = _team_points_in_specific_weeks(team_b, week_ids)
    return a_points, b_points


def _rank_by_h2h_among_group(teams: List[Team]) -> List[Team]:
    # Score each team by sum of points vs every other team in the group
    score_map: Dict[int, float] = defaultdict(float)
    for i in range(len(teams)):
        for j in range(i + 1, len(teams)):
            a = teams[i]
            b = teams[j]
            a_pts, b_pts = _head_to_head_points(a, b)
            score_map[a.id] += a_pts
            score_map[b.id] += b_pts

    # Fall back to 0 if no data; stable order by id to avoid jitter
    return sorted(teams, key=lambda t: (score_map.get(t.id, 0.0), t.id), reverse=True)


def compute_playoff_seeds(season, max_playoff_teams: int = 4) -> List[SeedInfo]:
    teams = list(Team.objects.filter(season=season))
    if not teams:
        return []

    first_map, second_map, total_map = _full_points_map(season)

    # Determine half winners
    max_first = max(first_map.values()) if first_map else 0.0
    max_second = max(second_map.values()) if second_map else 0.0

    first_half_winner_ids = [tid for tid, pts in first_map.items() if pts == max_first and pts > 0]
    second_half_winner_ids = [tid for tid, pts in second_map.items() if pts == max_second and pts > 0]

    id_to_team: Dict[int, Team] = {t.id: t for t in teams}

    half_winner_ids: List[int] = []
    for tid in first_half_winner_ids:
        if tid not in half_winner_ids:
            half_winner_ids.append(tid)
    for tid in second_half_winner_ids:
        if tid not in half_winner_ids:
            half_winner_ids.append(tid)

    half_winners: List[Team] = [id_to_team[tid] for tid in half_winner_ids]

    # Order half winners for seeding
    if len(half_winners) == 2:
        # Normal case: pick seed by higher total points
        ordered_half_winners = sorted(half_winners, key=lambda t: (total_map.get(t.id, 0.0), t.id), reverse=True)
        ordering_note = None
    elif len(half_winners) > 1:
        # Tie case: order using head-to-head within the tied group
        ordered_half_winners = _rank_by_h2h_among_group(half_winners)
        ordering_note = "Seeding determined by head-to-head among tied half winners"
    else:
        ordered_half_winners = half_winners
        ordering_note = None

    seeds: List[SeedInfo] = []
    used_ids: Set[int] = set()

    # Add half-winner seeds up to max_playoff_teams
    for idx, team in enumerate(ordered_half_winners[: max_playoff_teams] ):
        in_first = team.id in first_half_winner_ids
        in_second = team.id in second_half_winner_ids
        if in_first and in_second:
            source = 'both_halves'
        elif in_first:
            source = 'first_half'
        elif in_second:
            source = 'second_half'
        else:
            # Fallback: should not happen for half winners; default to wildcard semantics
            source = 'wildcard'
        seeds.append(
            SeedInfo(
                seed=len(seeds) + 1,
                team_id=team.id,
                team_name=_get_team_name(team),
                source=source,
                points_first_half=first_map.get(team.id, 0.0),
                points_second_half=second_map.get(team.id, 0.0),
                points_total=total_map.get(team.id, 0.0),
                tiebreak_note=ordering_note,
            )
        )
        used_ids.add(team.id)

    remaining_slots = max_playoff_teams - len(seeds)
    if remaining_slots <= 0:
        return seeds

    # Wildcard candidates: everyone else, sorted by total points
    wildcard_candidates = [t for t in teams if t.id not in used_ids]
    wildcard_candidates.sort(key=lambda t: (total_map.get(t.id, 0.0), t.id), reverse=True)

    # Process wildcards with tie-breaking by head-to-head when needed
    i = 0
    while remaining_slots > 0 and i < len(wildcard_candidates):
        # Group by total points (ties)
        pt = total_map.get(wildcard_candidates[i].id, 0.0)
        tie_group: List[Team] = [wildcard_candidates[i]]
        j = i + 1
        while j < len(wildcard_candidates) and abs(total_map.get(wildcard_candidates[j].id, 0.0) - pt) < 1e-9:
            tie_group.append(wildcard_candidates[j])
            j += 1

        # Rank within tie group by head-to-head amongst the group
        ranked_group = tie_group if len(tie_group) == 1 else _rank_by_h2h_among_group(tie_group)

        for team in ranked_group:
            if remaining_slots <= 0:
                break
            seeds.append(
                SeedInfo(
                    seed=len(seeds) + 1,
                    team_id=team.id,
                    team_name=_get_team_name(team),
                    source='wildcard',
                    points_first_half=first_map.get(team.id, 0.0),
                    points_second_half=second_map.get(team.id, 0.0),
                    points_total=total_map.get(team.id, 0.0),
                    tiebreak_note=(
                        'Wildcard tie resolved by head-to-head' if len(tie_group) > 1 else None
                    ),
                )
            )
            remaining_slots -= 1

        i = j

    return seeds


