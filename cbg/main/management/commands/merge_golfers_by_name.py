from django.core.management.base import BaseCommand
from django.db import transaction
from main.models import Golfer, Score, Round, GameEntry, SkinEntry, Handicap, GolferMatchup, Sub, Team
from django.db.models import Q


class Command(BaseCommand):
    help = 'Merge duplicate golfers by name - transfers all data from one golfer to another'

    def add_arguments(self, parser):
        parser.add_argument(
            '--from-name',
            type=str,
            required=True,
            help='Name of the golfer to merge FROM (will be deleted)'
        )
        parser.add_argument(
            '--to-name',
            type=str,
            required=True,
            help='Name of the golfer to merge TO (will be kept)'
        )
        parser.add_argument(
            '--test-run',
            action='store_true',
            help='Show what would be done without actually making changes'
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Skip confirmation prompts'
        )

    def get_golfer_stats(self, golfer):
        """Get statistics about a golfer's activity"""
        stats = {
            'scores_count': Score.objects.filter(golfer=golfer).count(),
            'rounds_count': Round.objects.filter(golfer=golfer).count(),
            'game_entries_count': GameEntry.objects.filter(golfer=golfer).count(),
            'skin_entries_count': SkinEntry.objects.filter(golfer=golfer).count(),
            'handicaps_count': Handicap.objects.filter(golfer=golfer).count(),
            'matchups_count': GolferMatchup.objects.filter(golfer=golfer).count(),
            'subs_count': Sub.objects.filter(absent_golfer=golfer).count(),
            'subbed_for_count': Sub.objects.filter(sub_golfer=golfer).count(),
            'teams_count': Team.objects.filter(golfers=golfer).count(),
        }
        return stats

    def handle(self, *args, **options):
        from_name = options['from_name']
        to_name = options['to_name']
        test_run = options['test_run']
        force = options['force']

        # Find the golfers by name
        try:
            from_golfer = Golfer.objects.get(name=from_name)
        except Golfer.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Golfer not found: "{from_name}"')
            )
            return

        try:
            to_golfer = Golfer.objects.get(name=to_name)
        except Golfer.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Golfer not found: "{to_name}"')
            )
            return

        if from_golfer.id == to_golfer.id:
            self.stdout.write(
                self.style.ERROR('Cannot merge a golfer with themselves!')
            )
            return

        self.stdout.write(
            self.style.SUCCESS(f'Preparing to merge golfers:')
        )
        self.stdout.write(f'FROM: "{from_golfer.name}" (ID: {from_golfer.id}) - Will be DELETED')
        self.stdout.write(f'TO:   "{to_golfer.name}" (ID: {to_golfer.id}) - Will be KEPT')
        self.stdout.write('')

        # Show current stats
        from_stats = self.get_golfer_stats(from_golfer)
        to_stats = self.get_golfer_stats(to_golfer)

        self.stdout.write('Current statistics:')
        self.stdout.write(f'FROM golfer stats: {from_stats}')
        self.stdout.write(f'TO golfer stats: {to_stats}')
        self.stdout.write('')

        if test_run:
            self.stdout.write(
                self.style.WARNING('TEST RUN - No changes will be made')
            )
            self.stdout.write('')
            self.stdout.write('The following operations would be performed:')
        else:
            if not force:
                self.stdout.write(
                    self.style.WARNING(
                        f'This will permanently delete "{from_golfer.name}" and transfer all their data to "{to_golfer.name}"'
                    )
                )
                confirm = input('Are you sure you want to proceed? (yes/no): ')
                if confirm.lower() != 'yes':
                    self.stdout.write('Merge cancelled.')
                    return

        # Perform the merge
        try:
            with transaction.atomic():
                if not test_run:
                    self.stdout.write('Starting merge...')

                # 1. Update Scores
                scores_to_update = Score.objects.filter(golfer=from_golfer)
                if scores_to_update.exists():
                    if test_run:
                        self.stdout.write(f'Would update {scores_to_update.count()} scores')
                    else:
                        scores_to_update.update(golfer=to_golfer)
                        self.stdout.write(f'Updated {scores_to_update.count()} scores')

                # 2. Update Rounds
                rounds_to_update = Round.objects.filter(golfer=from_golfer)
                if rounds_to_update.exists():
                    if test_run:
                        self.stdout.write(f'Would update {rounds_to_update.count()} rounds')
                    else:
                        rounds_to_update.update(golfer=to_golfer)
                        self.stdout.write(f'Updated {rounds_to_update.count()} rounds')

                # 3. Update Rounds where golfer is subbing for someone
                sub_rounds_to_update = Round.objects.filter(subbing_for=from_golfer)
                if sub_rounds_to_update.exists():
                    if test_run:
                        self.stdout.write(f'Would update {sub_rounds_to_update.count()} rounds where golfer is subbing for')
                    else:
                        sub_rounds_to_update.update(subbing_for=to_golfer)
                        self.stdout.write(f'Updated {sub_rounds_to_update.count()} rounds where golfer is subbing for')

                # 4. Update GameEntries
                game_entries_to_update = GameEntry.objects.filter(golfer=from_golfer)
                if game_entries_to_update.exists():
                    if test_run:
                        self.stdout.write(f'Would update {game_entries_to_update.count()} game entries')
                    else:
                        game_entries_to_update.update(golfer=to_golfer)
                        self.stdout.write(f'Updated {game_entries_to_update.count()} game entries')

                # 5. Update SkinEntries
                skin_entries_to_update = SkinEntry.objects.filter(golfer=from_golfer)
                if skin_entries_to_update.exists():
                    if test_run:
                        self.stdout.write(f'Would update {skin_entries_to_update.count()} skin entries')
                    else:
                        skin_entries_to_update.update(golfer=to_golfer)
                        self.stdout.write(f'Updated {skin_entries_to_update.count()} skin entries')

                # 6. Update Handicaps
                handicaps_to_update = Handicap.objects.filter(golfer=from_golfer)
                if handicaps_to_update.exists():
                    if test_run:
                        self.stdout.write(f'Would update {handicaps_to_update.count()} handicaps')
                    else:
                        handicaps_to_update.update(golfer=to_golfer)
                        self.stdout.write(f'Updated {handicaps_to_update.count()} handicaps')

                # 7. Update GolferMatchups (golfer field)
                matchups_to_update = GolferMatchup.objects.filter(golfer=from_golfer)
                if matchups_to_update.exists():
                    if test_run:
                        self.stdout.write(f'Would update {matchups_to_update.count()} golfer matchups (golfer field)')
                    else:
                        matchups_to_update.update(golfer=to_golfer)
                        self.stdout.write(f'Updated {matchups_to_update.count()} golfer matchups (golfer field)')

                # 8. Update GolferMatchups (opponent field)
                opponent_matchups_to_update = GolferMatchup.objects.filter(opponent=from_golfer)
                if opponent_matchups_to_update.exists():
                    if test_run:
                        self.stdout.write(f'Would update {opponent_matchups_to_update.count()} golfer matchups (opponent field)')
                    else:
                        opponent_matchups_to_update.update(opponent=to_golfer)
                        self.stdout.write(f'Updated {opponent_matchups_to_update.count()} golfer matchups (opponent field)')

                # 9. Update GolferMatchups (subbing_for_golfer field)
                sub_matchups_to_update = GolferMatchup.objects.filter(subbing_for_golfer=from_golfer)
                if sub_matchups_to_update.exists():
                    if test_run:
                        self.stdout.write(f'Would update {sub_matchups_to_update.count()} golfer matchups (subbing_for_golfer field)')
                    else:
                        sub_matchups_to_update.update(subbing_for_golfer=to_golfer)
                        self.stdout.write(f'Updated {sub_matchups_to_update.count()} golfer matchups (subbing_for_golfer field)')

                # 10. Update Subs (absent_golfer field)
                subs_to_update = Sub.objects.filter(absent_golfer=from_golfer)
                if subs_to_update.exists():
                    if test_run:
                        self.stdout.write(f'Would update {subs_to_update.count()} subs (absent_golfer field)')
                    else:
                        subs_to_update.update(absent_golfer=to_golfer)
                        self.stdout.write(f'Updated {subs_to_update.count()} subs (absent_golfer field)')

                # 11. Update Subs (sub_golfer field)
                sub_golfer_subs_to_update = Sub.objects.filter(sub_golfer=from_golfer)
                if sub_golfer_subs_to_update.exists():
                    if test_run:
                        self.stdout.write(f'Would update {sub_golfer_subs_to_update.count()} subs (sub_golfer field)')
                    else:
                        sub_golfer_subs_to_update.update(sub_golfer=to_golfer)
                        self.stdout.write(f'Updated {sub_golfer_subs_to_update.count()} subs (sub_golfer field)')

                # 12. Update Teams (ManyToMany relationship)
                teams_with_from_golfer = Team.objects.filter(golfers=from_golfer)
                if teams_with_from_golfer.exists():
                    if test_run:
                        self.stdout.write(f'Would update {teams_with_from_golfer.count()} teams')
                    else:
                        for team in teams_with_from_golfer:
                            team.golfers.remove(from_golfer)
                            if to_golfer not in team.golfers.all():
                                team.golfers.add(to_golfer)
                        self.stdout.write(f'Updated {teams_with_from_golfer.count()} teams')

                # 13. Delete the duplicate golfer
                if test_run:
                    self.stdout.write(f'Would delete golfer: "{from_golfer.name}" (ID: {from_golfer.id})')
                else:
                    from_golfer.delete()
                    self.stdout.write(f'Deleted golfer: "{from_golfer.name}" (ID: {from_golfer.id})')

                if not test_run:
                    self.stdout.write(
                        self.style.SUCCESS('Merge completed successfully!')
                    )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Error during merge: {e}')
            )
            if not test_run:
                self.stdout.write('Rolling back changes...')
            return

        # Show final stats
        if not test_run:
            final_stats = self.get_golfer_stats(to_golfer)
            self.stdout.write('')
            self.stdout.write('Final statistics for kept golfer:')
            self.stdout.write(f'{final_stats}')
        else:
            self.stdout.write('')
            self.stdout.write(
                self.style.SUCCESS('Test run completed. No changes were made.')
            ) 