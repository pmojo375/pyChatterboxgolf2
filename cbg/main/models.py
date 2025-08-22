from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings
from django.utils.text import slugify

class Golfer(models.Model):
    name = models.CharField(max_length=40)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Golfer'
        verbose_name_plural = 'Golfers'
    
    def __str__(self):
        return self.name
    
    
class Course(models.Model):
    name = models.CharField(max_length=80)
    city = models.CharField(max_length=80)
    state = models.CharField(max_length=80)
    
    class Meta:
        verbose_name = 'Course'
        verbose_name_plural = 'Courses'
    
    def __str__(self):
        return f'{self.name}'


class CourseConfig(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    name = models.CharField(max_length=80)
    effective_start = models.DateField(blank=True, null=True)
    effective_end = models.DateField(blank=True, null=True)
    
    class Meta:
        verbose_name = 'Course Config'
        verbose_name_plural = 'Course Configs'
    
    def clean(self):
        # Ensure at least one bound is set
        if not self.effective_start and not self.effective_end:
            raise ValidationError("Either effective_start or effective_end must be set.")

        # Ensure logical order if both are set
        if self.effective_start and self.effective_end:
            if self.effective_end < self.effective_start:
                raise ValidationError("effective_end cannot be before effective_start.")
    
    def __str__(self):
        return f'{self.course.name} - {self.name}' if self.name != "" else f'{self.course.name}'


class League(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=80, unique=True, blank=True, editable=False)
    managers = models.ManyToManyField(
        settings.AUTH_USER_MODEL, blank=True, related_name='managed_leagues'
    )

    class Meta:
        ordering = ['name']
        verbose_name_plural = "leagues"
        
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:  # only set once; don’t change on name edits
            base = slugify(self.name)
            slug = base or "league"
            i = 2
            while self.__class__.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{i}"
                i += 1
            self.slug = slug
        super().save(*args, **kwargs)


class Season(models.Model):
    
    SKINS_TYPE_CHOICES = [
        ("GROSS", "Gross"),
        ("NET", "Net"),
    ]
    
    year = models.IntegerField(primary_key=True)
    course_config = models.ForeignKey(CourseConfig, on_delete=models.PROTECT, null=True, blank=True)
    league = models.ForeignKey(
        League, on_delete=models.CASCADE, null=True, blank=True, related_name='seasons' # changed to allow db restore one last time
    )
    
    # skins and games settings
    playing_skins = models.BooleanField(default=False)
    skins_type = models.CharField(max_length=10, choices=SKINS_TYPE_CHOICES, default='GROSS')
    skins_entry_fee = models.IntegerField(default=5)
    playing_games = models.BooleanField(default=False)
    game_entry_fee = models.IntegerField(default=2)
    
    players_per_team = models.IntegerField(default=2)
    
    class Meta:
        ordering = ['-year']
        verbose_name = 'Season'
        verbose_name_plural = 'Seasons'
    
    def __str__(self):
        return f'{self.year}'


class Team(models.Model):
    season = models.ForeignKey(Season, on_delete=models.CASCADE)
    golfers = models.ManyToManyField(Golfer)

    class Meta:
        verbose_name = 'Team'
        verbose_name_plural = 'Teams'
    
    def __str__(self):
        golfers = self.golfers.all()
        if len(golfers) == 2:
            return f"{golfers[0].name} and {golfers[1].name}"
        else:
            return f"Team {self.pk}"


class Week(models.Model):
    season = models.ForeignKey(Season, on_delete=models.CASCADE)
    date = models.DateTimeField(default=timezone.now)
    rained_out = models.BooleanField(default=False)
    number = models.IntegerField()
    is_front = models.BooleanField()
    num_scores = models.IntegerField(null=True, blank=True)
    
    class Meta:
        ordering = ['-date']
        verbose_name = 'Week'
        verbose_name_plural = 'Weeks'
    
    def clean(self):
        from django.core.exceptions import ValidationError
        # Check for duplicate non-rained-out weeks
        if not self.rained_out:
            existing_non_rained = Week.objects.filter(
                season=self.season, 
                number=self.number, 
                rained_out=False
            ).exclude(id=self.id)
            if existing_non_rained.exists():
                raise ValidationError(
                    f'Cannot have multiple non-rained-out weeks for season {self.season.year}, week {self.number}'
                )
    
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
    week = models.ForeignKey(Week, on_delete=models.CASCADE, null=True, blank=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Game'
        verbose_name_plural = 'Games'
    
    def __str__(self):
        return self.name


class GameEntry(models.Model):
    game = models.ForeignKey(Game, on_delete=models.CASCADE)
    golfer = models.ForeignKey(Golfer, on_delete=models.CASCADE)
    week = models.ForeignKey(Week, on_delete=models.CASCADE)
    winner = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['game', 'golfer', 'week']
        verbose_name = 'Game Entry'
        verbose_name_plural = 'Game Entries'
    
    def __str__(self):
        return f'{self.game.name} - {self.golfer.name} - {self.week.date.strftime("%Y-%m-%d")}'


class SkinEntry(models.Model):
    golfer = models.ForeignKey(Golfer, on_delete=models.CASCADE)
    week = models.ForeignKey(Week, on_delete=models.CASCADE)
    winner = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ('golfer', 'week')
        verbose_name = 'Skin Entry'
        verbose_name_plural = 'Skin Entries'
    
    def __str__(self):
        return f'{self.golfer.name} - {self.week.date.strftime("%Y-%m-%d")}'


class Hole(models.Model):
    config = models.ForeignKey(CourseConfig, on_delete=models.CASCADE, related_name="holes", null=True, blank=True)
    number = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(18)])
    par = models.IntegerField(validators=[MinValueValidator(3), MaxValueValidator(5)])
    handicap = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(18)])
    handicap9 = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(9)])
    yards = models.IntegerField(validators=[MinValueValidator(1)])
    class Meta:
        ordering = ['number']
        unique_together = ['config', 'number']
        verbose_name = 'Hole'
        verbose_name_plural = 'Holes'
    
    def __str__(self):
        return f'Hole {self.number} ({self.config})'

class Score(models.Model):
    golfer = models.ForeignKey(Golfer, on_delete=models.CASCADE)
    week = models.ForeignKey(Week, on_delete=models.CASCADE)
    hole = models.ForeignKey(Hole, on_delete=models.CASCADE)
    score = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(10)])  # Increased max to 20 for realistic golf scores
    
    class Meta:
        unique_together = ('golfer', 'week', 'hole')
        verbose_name = 'Score'
        verbose_name_plural = 'Scores'
    
    def __str__(self):
        return f'{self.golfer.name} - {self.week.date.strftime("%Y-%m-%d")} - {self.hole.number}'

class Handicap(models.Model):
    golfer = models.ForeignKey(Golfer, on_delete=models.CASCADE)
    week = models.ForeignKey(Week, on_delete=models.CASCADE)
    handicap = models.FloatField()
    
    class Meta:
        unique_together = ['golfer', 'week']
        ordering = ['-week__date']
        verbose_name = 'Handicap'
        verbose_name_plural = 'Handicaps'
    
    def __str__(self):
        return f'{self.golfer.name} - {self.week.date.strftime("%Y-%m-%d")} - {self.handicap}'

class Matchup(models.Model):
    week = models.ForeignKey(Week, on_delete=models.CASCADE)
    teams = models.ManyToManyField(Team)
    
    class Meta:
        ordering = ['-week__date']
        verbose_name = 'Matchup'
        verbose_name_plural = 'Matchups'
    
    def __str__(self):
        teams = self.teams.all()
        if len(teams) >= 2:
            return f'{self.week.date.strftime("%Y-%m-%d")} - {teams[0]} vs {teams[1]}'
        return f'{self.week.date.strftime("%Y-%m-%d")} - Matchup'

class Sub(models.Model):
    week = models.ForeignKey(Week, on_delete=models.CASCADE)
    absent_golfer = models.ForeignKey(Golfer, related_name='absent', on_delete=models.CASCADE)
    sub_golfer = models.ForeignKey(Golfer, related_name='sub', on_delete=models.CASCADE, null=True, blank=True)
    no_sub = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['week', 'absent_golfer']
        ordering = ['-week__date']
        verbose_name = 'Substitution'
        verbose_name_plural = 'Substitutions'
    
    def save(self, *args, **kwargs):
        # Ensure consistency: if no_sub is True, clear sub_golfer
        if self.no_sub:
            self.sub_golfer = None
        super().save(*args, **kwargs)
    
    def __str__(self):
        if self.no_sub:
            return f'{self.week.date.strftime("%Y-%m-%d")} - {self.absent_golfer.name} (No Sub)'
        elif self.sub_golfer:
            return f'{self.week.date.strftime("%Y-%m-%d")} - {self.sub_golfer.name} for {self.absent_golfer.name}'
        return f'{self.week.date.strftime("%Y-%m-%d")} - {self.absent_golfer.name}'

class Points(models.Model):
    golfer = models.ForeignKey(Golfer, on_delete=models.CASCADE)
    week = models.ForeignKey(Week, on_delete=models.CASCADE)
    hole = models.ForeignKey(Hole, on_delete=models.CASCADE)
    score = models.ForeignKey(Score, on_delete=models.CASCADE)
    opponent = models.ForeignKey(Golfer, on_delete=models.CASCADE, related_name='points_against', null=True, blank=True)
    points = models.FloatField(validators=[MinValueValidator(0)])
    
    class Meta:
        unique_together = ['golfer', 'week', 'hole', 'opponent']
        verbose_name = 'Point'
        verbose_name_plural = 'Points'
    
    def __str__(self):
        return f'{self.golfer.name} - {self.week.date.strftime("%Y-%m-%d")} - Hole {self.hole.number} - {self.points} pts'
        
class Round(models.Model):
    golfer = models.ForeignKey(Golfer, on_delete=models.CASCADE)
    is_sub = models.BooleanField(default=False)
    week = models.ForeignKey(Week, on_delete=models.CASCADE)
    matchup = models.ForeignKey(Matchup, on_delete=models.CASCADE)
    golfer_matchup = models.ForeignKey('GolferMatchup', on_delete=models.CASCADE)
    handicap = models.ForeignKey(Handicap, on_delete=models.CASCADE)
    points = models.ManyToManyField(Points)
    scores = models.ManyToManyField(Score)
    gross = models.IntegerField(validators=[MinValueValidator(1)])
    net = models.IntegerField(validators=[MinValueValidator(1)])
    round_points = models.FloatField(validators=[MinValueValidator(0)])
    total_points = models.FloatField(validators=[MinValueValidator(0)])
    subbing_for = models.ForeignKey(Golfer, null=True, blank=True, on_delete=models.SET_NULL, related_name='rounds_subbed_for')

    class Meta:
        unique_together = ('golfer_matchup', 'week')
        ordering = ['-week__date']
        verbose_name = 'Round'
        verbose_name_plural = 'Rounds'
    
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
    opponent_team_no_subs = models.BooleanField(default=False)

    # If the golfer is subbing for another golfer, this field will be set otherwise it will be null
    subbing_for_golfer = models.ForeignKey(Golfer, related_name='subbing_for_golfer', on_delete=models.CASCADE, null=True, blank=True)
    
    class Meta:
        unique_together = ['week', 'golfer', 'opponent']
        ordering = ['-week__date']
        verbose_name = 'Golfer Matchup'
        verbose_name_plural = 'Golfer Matchups'
    
    def __str__(self):
        return f'{self.week.date.strftime("%Y-%m-%d")} - {self.golfer.name} vs {self.opponent.name}'
    
class RandomDrawnTeam(models.Model):
    # This model is used to store the random drawn team that plays in place of an absent team that could not find subs
    week = models.ForeignKey(Week, on_delete=models.CASCADE)
    absent_team = models.ForeignKey(Team, related_name='absent_team', on_delete=models.CASCADE)
    drawn_team = models.ForeignKey(Team, related_name='drawn_team', on_delete=models.CASCADE)
    
    class Meta:
        unique_together = ['week', 'absent_team']
        ordering = ['-week__date']
        verbose_name = 'Random Drawn Team'
        verbose_name_plural = 'Random Drawn Teams'
    
    def __str__(self):
        return f'{self.week.date.strftime("%Y-%m-%d")} - {self.drawn_team} plays for {self.absent_team}'