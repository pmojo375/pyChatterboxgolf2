from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db import transaction
from main.models import Score, GolferMatchup, Sub, Team, Matchup, Week
from main.helper import generate_golfer_matchups, calculate_and_save_handicaps_for_season, get_week, process_week
from main.helper import get_hcp
from main.tasks import process_week_async, generate_matchups_async

@receiver(post_save, sender=Score)
def score_updated(sender, instance, created, **kwargs):
    # 'instance' is the Score object that was saved

    week = instance.week
    
    number_of_scores = Score.objects.filter(week=week).count()
    
    # check if the scores are for full rounds (divisible by 9)
    if number_of_scores % 9 == 0:
        no_sub_golfer_count = Sub.objects.filter(week=week, no_sub=True).count()
        
        scores_needed = ((Team.objects.filter(season=week.season).count() * 2) - no_sub_golfer_count) * 9
        
        if number_of_scores == scores_needed:
            # Use on_commit to ensure the Score save is committed before processing
            transaction.on_commit(lambda: process_week_async.delay(week.id))
            # all scores entered... Process week asynchronously.
        
@receiver(post_delete, sender=Score)
def score_deleted(sender, instance, **kwargs):
    pass
    #print('Score Deleted')

@receiver(post_save, sender=Sub)
def sub_updated(sender, instance, created, **kwargs):

    print('Sub Updated')
    
    # Use on_commit to ensure the Sub save is committed before updating week and generating matchups
    def update_week_and_matchups():
        no_sub_golfer_count = Sub.objects.filter(week=instance.week, no_sub=True).count()
        scores_needed = ((Team.objects.filter(season=instance.week.season).count() * 2) - no_sub_golfer_count) * 9
        
        instance.week.num_scores = scores_needed
        instance.week.save()

        # Generate matchups asynchronously
        generate_matchups_async.delay(instance.week.id)
    
    transaction.on_commit(update_week_and_matchups)

@receiver(post_delete, sender=Sub)
def sub_deleted(sender, instance, **kwargs):
    
    # Use on_commit to ensure the Sub delete is committed before updating week and generating matchups
    def update_week_and_matchups():
        no_sub_golfer_count = Sub.objects.filter(week=instance.week, no_sub=True).count()
        scores_needed = ((Team.objects.filter(season=instance.week.season).count() * 2) - no_sub_golfer_count) * 9
        
        instance.week.num_scores = scores_needed
        instance.week.save()

        # Generate matchups asynchronously
        generate_matchups_async.delay(instance.week.id)
    
    transaction.on_commit(update_week_and_matchups)

@receiver(post_save, sender=Matchup)
def matchup_created(sender, instance, created, **kwargs):
    """
    When a matchup is created (schedule is entered), generate initial golfer matchups
    when all matchups for the week have been entered.
    """
    if created:
        # Use on_commit to ensure the Matchup save is committed before checking and generating matchups
        def check_and_generate_matchups():
            week = instance.week
            total_teams = Team.objects.filter(season=week.season).count()
            total_matchups = Matchup.objects.filter(week=week).count()
            
            # Generate matchups when we have all the matchups (teams/2 since each matchup has 2 teams)
            # and no golfer matchups exist yet
            if total_matchups == total_teams // 2 and not GolferMatchup.objects.filter(week=week).exists():
                print(f'All matchups entered for Week {week.number}. Generating initial golfer matchups.')
                generate_matchups_async.delay(week.id)
        
        transaction.on_commit(check_and_generate_matchups)