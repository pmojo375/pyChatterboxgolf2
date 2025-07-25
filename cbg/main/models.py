from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
class Golfer(models.Model):
    name = models.CharField(max_length=40)
    
    def __str__(self):
        return self.name

class Season(models.Model):
    year = models.IntegerField(primary_key=True)
    
    def __str__(self):
        return f'{self.year}'

class Team(models.Model):
    season = models.ForeignKey(Season, on_delete=models.CASCADE)
    golfers = models.ManyToManyField(Golfer)

    def __str__(self):
        golfers = self.golfers.all()
        if len(golfers) == 2:
            return f"{golfers[0].name} and {golfers[1].name}"
        else:
            return f"Team {self.pk}"

class Week(models.Model):
    season = models.ForeignKey(Season, on_delete=models.CASCADE)
    date = models.DateTimeField(default=timezone.now)
    rained_out = models.BooleanField()
    number = models.IntegerField()
    is_front = models.BooleanField()
    num_scores = models.IntegerField()
    
    def save(self, *args, **kwargs):
        # Calculate default number of scores based on season's team count
        if self.num_scores is None:  # Only calculate if not already set
            self.num_scores = Team.objects.filter(season=self.season).count() * 9 * 2
        super().save(*args, **kwargs)
        
    def __str__(self):
        #print date in format 2022-01-01 with week number
        if self.rained_out:
            return f'{self.date.strftime("%Y-%m-%d")} (Week {self.number}) - Rained Out'
        else:
            return f'{self.date.strftime("%Y-%m-%d")} (Week {self.number})'


class Game(models.Model):
    name = models.CharField(max_length=80)
    desc = models.TextField(max_length=480)
    week = models.ForeignKey(Week, on_delete=models.CASCADE, null=True)
    
    def __str__(self):
        return self.name


class GameEntry(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    golfer = models.ForeignKey(Golfer, on_delete=models.CASCADE)
    week = models.ForeignKey(Week, on_delete=models.CASCADE)
    winner = models.BooleanField(default=False)
    
    def __str__(self):
        return f'{self.game.name} - {self.golfer.name} - {self.week.date.strftime("%Y-%m-%d")}'


class SkinEntry(models.Model):
    golfer = models.ForeignKey(Golfer, on_delete=models.CASCADE)
    week = models.ForeignKey(Week, on_delete=models.CASCADE)
    winner = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ('golfer', 'week')
    
    def __str__(self):
        return f'{self.golfer.name} - {self.week.date.strftime("%Y-%m-%d")}'


class Hole(models.Model):
    number = models.IntegerField()
    par = models.IntegerField()
    handicap = models.IntegerField()
    handicap9 = models.IntegerField()
    yards = models.IntegerField()
    season = models.ForeignKey(Season, on_delete=models.CASCADE)
    
    def __str__(self):
        return f'Hole {self.number} season {self.season.year}'

class Score(models.Model):
    golfer = models.ForeignKey(Golfer, on_delete=models.CASCADE)
    week = models.ForeignKey(Week, on_delete=models.CASCADE)
    hole = models.ForeignKey(Hole, on_delete=models.CASCADE)
    score = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(10)])
    
    def __str__(self):
        return f'{self.golfer.name} - {self.week.date.strftime("%Y-%m-%d")} - {self.hole.number}'
    class Meta:
        unique_together = ('golfer', 'week', 'hole')

class Handicap(models.Model):
    golfer = models.ForeignKey(Golfer, on_delete=models.CASCADE)
    week = models.ForeignKey(Week, on_delete=models.CASCADE)
    handicap = models.FloatField()
    
    def __str__(self):
        return f'{self.golfer.name} - {self.week.date.strftime("%Y-%m-%d")} - {self.handicap}'

class Matchup(models.Model):
    week = models.ForeignKey(Week, on_delete=models.CASCADE)
    teams = models.ManyToManyField(Team)
    
    def __str__(self):
        return f'{self.week.date.strftime("%Y-%m-%d")} - {self.teams.all()[0]} vs {self.teams.all()[1]}'

class Sub(models.Model):
    week = models.ForeignKey(Week, on_delete=models.CASCADE)
    absent_golfer = models.ForeignKey(Golfer, related_name='absent', on_delete=models.CASCADE)
    sub_golfer = models.ForeignKey(Golfer, related_name='sub', on_delete=models.CASCADE, null=True)
    no_sub = models.BooleanField(default=False)

class Points(models.Model):
    golfer = models.ForeignKey(Golfer, on_delete=models.CASCADE)
    week = models.ForeignKey(Week, on_delete=models.CASCADE)
    hole = models.ForeignKey(Hole, on_delete=models.CASCADE)
    score = models.ForeignKey(Score, on_delete=models.CASCADE)
    points = models.FloatField()
    
class Round(models.Model):
    golfer = models.ForeignKey(Golfer, on_delete=models.CASCADE)
    is_sub = models.BooleanField(default=False)
    week = models.ForeignKey(Week, on_delete=models.CASCADE)
    matchup = models.ForeignKey(Matchup, on_delete=models.CASCADE)
    golfer_matchup = models.ForeignKey('GolferMatchup', on_delete=models.CASCADE, null=True)
    handicap = models.ForeignKey(Handicap, on_delete=models.CASCADE)
    points = models.ManyToManyField(Points)
    scores = models.ManyToManyField(Score)
    gross = models.IntegerField()
    net = models.IntegerField()
    round_points = models.FloatField()
    total_points = models.FloatField(null=True)
    subbing_for = models.ForeignKey(Golfer, null=True, blank=True, on_delete=models.SET_NULL, related_name='rounds_subbed_for')

    class Meta:
        unique_together = ('golfer_matchup', 'week')
    
    def __str__(self):
        sub_text = " (SUB)" if self.is_sub else ""
        subbing_text = f" for {self.subbing_for.name}" if self.subbing_for else ""
        return f"{self.golfer.name}{sub_text}{subbing_text} - {self.week.date.strftime('%Y-%m-%d')} - Gross: {self.gross}, Net: {self.net}"
        
class GolferMatchup(models.Model):
    week = models.ForeignKey(Week, related_name='week', on_delete=models.CASCADE)
    is_A = models.BooleanField(db_column="is_a", default=False)
    golfer = models.ForeignKey(Golfer, on_delete=models.CASCADE)
    opponent = models.ForeignKey(Golfer, related_name='opponent', on_delete=models.CASCADE)
    is_teammate_subbing = models.BooleanField(default=False)

    # If the golfer is subbing for another golfer, this field will be set otherwise it will be null
    subbing_for_golfer = models.ForeignKey(Golfer, related_name='subbing_for_golfer', on_delete=models.CASCADE, null=True)
    
    def __str__(self):
        return f'{self.week.date.strftime("%Y-%m-%d")} - {self.golfer.name} vs {self.opponent.name}'
    
class RandomDrawnTeam(models.Model):
    # This model is used to store the random drawn team that plays in place of an absent team that could not find subs
    week = models.ForeignKey(Week, on_delete=models.CASCADE)
    absent_team = models.ForeignKey(Team, related_name='absent_team', on_delete=models.CASCADE)
    drawn_team = models.ForeignKey(Team, related_name='drawn_team', on_delete=models.CASCADE)
    
    def __str__(self):
        return f'{self.week.date.strftime("%Y-%m-%d")} - {self.drawn_team} plays for {self.absent_team}'