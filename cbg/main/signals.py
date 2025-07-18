from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from main.models import Score, GolferMatchup, Sub, Team, Matchup, Week
from main.helper import generate_golfer_matchups, calculate_and_save_handicaps_for_season, get_week, process_week
from main.helper import get_hcp

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
            process_week(week)
            # all scores entered... Process week.
        
@receiver(post_delete, sender=Score)
def score_deleted(sender, instance, **kwargs):
    pass
    #print('Score Deleted')

@receiver(post_save, sender=Sub)
def sub_updated(sender, instance, created, **kwargs):

    print('Sub Updated')
        
    no_sub_golfer_count = Sub.objects.filter(week=instance.week, no_sub=True).count()
    scores_needed = ((Team.objects.filter(season=instance.week.season).count() * 2) - no_sub_golfer_count) * 9
    
    instance.week.num_scores = scores_needed
    instance.week.save()

    generate_golfer_matchups(instance.week)

@receiver(post_delete, sender=Sub)
def sub_deleted(sender, instance, **kwargs):
    
    no_sub_golfer_count = Sub.objects.filter(week=instance.week, no_sub=True).count()
    scores_needed = ((Team.objects.filter(season=instance.week.season).count() * 2) - no_sub_golfer_count) * 9
    
    instance.week.num_scores = scores_needed
    instance.week.save()

    generate_golfer_matchups(instance.week)

@receiver(post_save, sender=Matchup)
def matchup_created(sender, instance, created, **kwargs):
    """
    When a matchup is created (schedule is entered), generate initial golfer matchups
    when all matchups for the week have been entered.
    """
    if created:
        week = instance.week
        total_teams = Team.objects.filter(season=week.season).count()
        total_matchups = Matchup.objects.filter(week=week).count()
        
        # Generate matchups when we have all the matchups (teams/2 since each matchup has 2 teams)
        # and no golfer matchups exist yet
        if total_matchups == total_teams // 2 and not GolferMatchup.objects.filter(week=week).exists():
            print(f'All matchups entered for Week {week.number}. Generating initial golfer matchups.')
            generate_golfer_matchups(week)