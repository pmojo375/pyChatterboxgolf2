from django.db import models


class Golfer(models.Model):
    name = models.CharField(max_length=40)


class Season(models.Model):
    year = models.IntegerField(primary_key=True)


class Team(models.Model):
    season = models.ForeignKey(Season, on_delete=models.CASCADE)
    golfers = models.ManyToManyField(Golfer)


class Week(models.Model):
    season = models.ForeignKey(Season, on_delete=models.CASCADE)
    date = models.DateTimeField()
    rained_out = models.BooleanField()
    number = models.IntegerField()
    is_front = models.BooleanField()


class Game(models.Model):
    name = models.CharField(max_length=80)
    desc = models.TextField(max_length=480)
    week = models.ForeignKey(Week, on_delete=models.CASCADE, null=True)


class GameEntry(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    golfer = models.ForeignKey(Golfer, on_delete=models.CASCADE)
    week = models.ForeignKey(Week, on_delete=models.CASCADE)
    winner = models.BooleanField(default=False)


class SkinEntry(models.Model):
    golfer = models.ForeignKey(Golfer, on_delete=models.CASCADE)
    week = models.ForeignKey(Week, on_delete=models.CASCADE)
    winner = models.BooleanField(default=False)


class Hole(models.Model):
    number = models.IntegerField()
    par = models.IntegerField()
    handicap = models.IntegerField()
    handicap9 = models.IntegerField()
    yards = models.IntegerField()
    season = models.ForeignKey(Season, on_delete=models.CASCADE)


class Score(models.Model):
    golfer = models.ForeignKey(Golfer, on_delete=models.CASCADE)
    week = models.ForeignKey(Week, on_delete=models.CASCADE)
    hole = models.ForeignKey(Hole, on_delete=models.CASCADE)
    score = models.IntegerField()


class Handicap(models.Model):
    golfer = models.ForeignKey(Golfer, on_delete=models.CASCADE)
    week = models.ForeignKey(Week, on_delete=models.CASCADE)
    handicap = models.FloatField()


class Matchup(models.Model):
    week = models.ForeignKey(Week, on_delete=models.CASCADE)
    teams = models.ManyToManyField(Team)


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
    handicap = models.ForeignKey(Handicap, on_delete=models.CASCADE)
    points = models.ManyToManyField(Points)
    scores = models.ManyToManyField(Score)
    gross = models.IntegerField()
    net = models.IntegerField()
    round_points = models.FloatField()
    
    class Meta:
        unique_together = ('golfer', 'week')
        
    def calculate_gross(self):
        return sum(score.score for score in self.scores.all())
    
    def calculate_net(self):
        if self.gross is not None and self.handicap is not None:
            handicap_value = round(self.handicap.handicap)
            return self.gross - handicap_value
        return None
    
    def save(self, *args, **kwargs):
        self.gross = self.calculate_gross()
        self.net = self.calculate_net()
        super().save(*args, **kwargs)
    