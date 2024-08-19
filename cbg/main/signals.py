from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from main.models import Score, GolferMatchup, Sub, Team, Matchup, Week
from main.helper import generate_golfer_matchups, calculate_and_save_handicaps_for_season, get_week
from main.helper import get_hcp

@receiver(post_save, sender=Score)
def score_updated(sender, instance, created, **kwargs):
    # 'instance' is the Score object that was saved
    
    if created:
        print('Score Created')
    else:
        print('Score Modified')
    
    week = instance.week
    
    number_of_scores = Score.objects.filter(week=week).count()
    
    # check if the scores are for full rounds (divisible by 9)
    if number_of_scores % 9 == 0:
        no_sub_golfer_count = Sub.objects.filter(week=week, no_sub=True).count()
        
        scores_needed = ((Team.objects.filter(season=week.season).count() * 2) - no_sub_golfer_count) * 9
        
        if number_of_scores == scores_needed:
            pass
            # all scores entered... Process week.
        
@receiver(post_delete, sender=Score)
def score_deleted(sender, instance, **kwargs):
    print('Score Deleted')

@receiver(post_save, sender=Sub)
def sub_updated(sender, instance, created, **kwargs):
    if created:
        print('Sub Created')
    else:
        print('Sub Modified')
        
    no_sub_golfer_count = Sub.objects.filter(week=instance.week, no_sub=True).count()
    scores_needed = ((Team.objects.filter(season=instance.week.season).count() * 2) - no_sub_golfer_count) * 9
    
    instance.week.num_scores = scores_needed
    instance.week.save()

@receiver(post_delete, sender=Sub)
def sub_deleted(sender, instance, **kwargs):
    print('Score Deleted')
    
    no_sub_golfer_count = Sub.objects.filter(week=instance.week, no_sub=True).count()
    scores_needed = ((Team.objects.filter(season=instance.week.season).count() * 2) - no_sub_golfer_count) * 9
    
    instance.week.num_scores = scores_needed
    instance.week.save()

    