from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
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
    date = models.DateTimeField()
    rained_out = models.BooleanField()
    number = models.IntegerField()
    is_front = models.BooleanField()
    
    def __str__(self):
        #print date in format 2022-01-01 with week number
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
    sub_golfer = models.ForeignKey(Golfer, related_name='sub', on_delete=models.CASCADE)

class Points(models.Model):
    golfer = models.ForeignKey(Golfer, on_delete=models.CASCADE)
    week = models.ForeignKey(Week, on_delete=models.CASCADE)
    hole = models.ForeignKey(Hole, on_delete=models.CASCADE)
    score = models.ForeignKey(Score, on_delete=models.CASCADE)
    points = models.FloatField()
    
class Round(models.Model):
    golfer = models.ForeignKey(Golfer, on_delete=models.CASCADE)
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
    
    class Meta:
        unique_together = ('golfer_matchup', 'week')
        
class GolferMatchup(models.Model):
    week = models.ForeignKey(Week, related_name='week', on_delete=models.CASCADE)
    is_A = models.BooleanField(default=False)
    golfer = models.ForeignKey(Golfer, on_delete=models.CASCADE)
    opponent = models.ForeignKey(Golfer, related_name='opponent', on_delete=models.CASCADE)
    
    def __str__(self):
        return f'{self.week.date.strftime("%Y-%m-%d")} - {self.golfer.name} vs {self.opponent.name}'
        