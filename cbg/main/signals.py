from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from main.models import Score

@receiver(post_save, sender=Score)
def score_updated(sender, instance, created, **kwargs):
    # Logic to handle score update
    # 'instance' is the Score object that was saved
    if created:
        # Runs when a new score is entered
        
        # Need to check if all scores are entered for the week and then run my calculations
        
        print('New Score Added')
    else:
        # This runs if an existing Score instance is updated
        
        # Run recalculation of data
        
        print('Score Modified')
        
@receiver(post_delete, sender=Score)
def score_deleted(sender, instance, **kwargs):
    # Logic to handle the deletion of a score
    print('Score Deleted')

