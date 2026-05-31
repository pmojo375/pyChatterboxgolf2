from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from decouple import config

from main.helper import get_current_season
from main.league_scope import resolve_league
from main.models import Golfer, Season

User = get_user_model()


def base_username_from_name(name):
    slug = slugify(name).replace('-', '_')
    return (slug or 'golfer')[:150]


def allocate_username(base, reserved_usernames):
    candidate = base
    suffix_num = 2
    while (
        candidate in reserved_usernames
        or User.objects.filter(username=candidate).exists()
    ):
        suffix = f'_{suffix_num}'
        candidate = f'{base[:150 - len(suffix)]}{suffix}'
        suffix_num += 1
    reserved_usernames.add(candidate)
    return candidate


def split_golfer_name(name):
    parts = name.rsplit(' ', 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return name, ''


class Command(BaseCommand):
    help = (
        'Create Django login accounts for team golfers in a season. '
        'Skips subs and golfers who already have a linked user.'
    )

    def add_arguments(self, parser):
        parser.add_argument(
            '--league-slug',
            type=str,
            default=None,
            help='League slug (default: DEFAULT_LEAGUE_SLUG from settings).',
        )
        parser.add_argument(
            '--year',
            type=int,
            default=None,
            help='Season year (default: latest season for the league).',
        )
        parser.add_argument(
            '--password',
            type=str,
            default=None,
            help=(
                'Default password for new accounts. '
                'If omitted, uses DEFAULT_GOLFER_PASSWORD from the environment.'
            ),
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Print actions without creating users or updating golfers.',
        )

    def handle(self, *args, **options):
        league = resolve_league(options['league_slug'])
        if league is None:
            raise CommandError('No league found.')

        year = options['year']
        if year is not None:
            season = Season.objects.filter(league=league, year=year).first()
            if season is None:
                raise CommandError(
                    f'No season for league "{league.slug}" in {year}.'
                )
        else:
            season = get_current_season(league=league)
            if season is None:
                raise CommandError(
                    f'No season found for league "{league.slug}". '
                    'Pass --year to target a specific season.'
                )

        password = options['password'] or config('DEFAULT_GOLFER_PASSWORD', default='')
        if not password and not options['dry_run']:
            raise CommandError(
                'Provide --password or set DEFAULT_GOLFER_PASSWORD in the environment.'
            )

        team_golfers = (
            Golfer.objects.filter(team__season=season)
            .distinct()
            .order_by('name', 'pk')
        )

        if not team_golfers.exists():
            self.stdout.write(
                self.style.WARNING(
                    f'No team golfers found for {league.name} {season.year}.'
                )
            )
            return

        reserved_usernames = set(
            User.objects.values_list('username', flat=True)
        )
        created = 0
        skipped = 0
        dry_run = options['dry_run']

        self.stdout.write(
            f'Target: {league.name} {season.year} '
            f'({team_golfers.count()} team golfer(s))'
        )
        if dry_run:
            self.stdout.write(self.style.WARNING('Dry run — no changes will be saved.'))

        with transaction.atomic():
            for golfer in team_golfers:
                if golfer.user_id:
                    self.stdout.write(
                        f'  skip {golfer.name!r}: already linked to '
                        f'{golfer.user.username!r}'
                    )
                    skipped += 1
                    continue

                base = base_username_from_name(golfer.name)
                username = allocate_username(base, reserved_usernames)
                first_name, last_name = split_golfer_name(golfer.name)

                if dry_run:
                    self.stdout.write(
                        f'  would create {username!r} for {golfer.name!r}'
                    )
                    created += 1
                    continue

                user = User.objects.create(
                    username=username,
                    password=make_password(password),
                    first_name=first_name[:150],
                    last_name=last_name[:150],
                    is_staff=False,
                    is_superuser=False,
                )
                golfer.user = user
                golfer.save(update_fields=['user'])
                self.stdout.write(
                    self.style.SUCCESS(
                        f'  created {username!r} for {golfer.name!r}'
                    )
                )
                created += 1

            if dry_run:
                transaction.set_rollback(True)

        summary = f'Done: {created} account(s) created, {skipped} skipped.'
        self.stdout.write(self.style.SUCCESS(summary))
