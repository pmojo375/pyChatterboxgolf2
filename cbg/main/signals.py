from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from main.models import Score, GolferMatchup
from main.helper import generate_golfer_matchups, calculate_and_save_handicaps_for_season, get_week

@receiver(post_save, sender=Score)
def score_updated(sender, instance, created, **kwargs):
    # Logic to handle score update
    # 'instance' is the Score object that was saved
    if created:
        # Runs when a new score is entered
        
        week = instance.week
        
        current_week = get_week()
        
        number_of_scores = Score.objects.filter(week=week).count()
        
        if number_of_scores % 9 == 0:
            generate_golfer_matchups(week)
            print(GolferMatchup.objects.filter(week=week).count())
            
            if GolferMatchup.objects.filter(week=week).count() == 10:
                calculate_and_save_handicaps_for_season(week.season, week)
                print('Run handicap calcs and points')
    else:
        # This runs if an existing Score instance is updated
        
        week = instance.week
        
        current_week = get_week()
        
        
        number_of_scores = Score.objects.filter(week=week).count()
        
        if number_of_scores % 9 == 0:
            generate_golfer_matchups(week)
            print(GolferMatchup.objects.filter(week=week).count())
            
            if GolferMatchup.objects.filter(week=week).count() == 10:
                calculate_and_save_handicaps_for_season(week.season, week)
                print('Run handicap calcs and points')
        
        
        print('Score Modified')
        
@receiver(post_delete, sender=Score)
def score_deleted(sender, instance, **kwargs):
    # Logic to handle the deletion of a score
    print('Score Deleted')

