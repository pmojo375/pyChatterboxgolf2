"""Resolve which league a request belongs to and scope Season queries."""

from django.conf import settings

from main.models import League


def get_default_league():
    """Primary league for this site when the URL does not specify one."""
    slug = getattr(settings, 'DEFAULT_LEAGUE_SLUG', '') or None
    if slug:
        league = League.objects.filter(slug=slug).first()
        if league:
            return league
    return League.objects.order_by('pk').first()


def resolve_league(slug=None):
    """Return the League for an optional URL slug, else the default league."""
    if slug:
        league = League.objects.filter(slug=slug).first()
        if league:
            return league
    return get_default_league()


def first_year_in_path_parts(parts):
    """First path segment that looks like a 4-digit calendar year ([12]ddd)."""
    for p in parts:
        if len(p) == 4 and p.isdigit() and p[0] in '12':
            return int(p)
    return None


def league_and_year_from_path(path):
    """
    Parse /league-slug/... vs legacy /2024/...

    Returns (league, year_or_none). Year is the first [12]ddd segment after
    the league slug (if any), or the first such segment in the full path for
    legacy URLs.
    """
    parts = [p for p in path.strip('/').split('/') if p]
    if not parts:
        return get_default_league(), None
    first = parts[0]
    if League.objects.filter(slug=first).exists():
        league = League.objects.get(slug=first)
        year = first_year_in_path_parts(parts[1:])
        return league, year
    return get_default_league(), first_year_in_path_parts(parts)
