from django import forms
from django.core.exceptions import ValidationError
from django.db.models import Q
from main.models import *
from main.helper import *
from django.utils import timezone
from main.helper import get_playing_golfers_for_week, get_earliest_week_without_full_matchups, get_next_week
from main.league_scope import get_default_league


def _seasons_for_default_league():
    lg = get_default_league()
    if not lg:
        return Season.objects.none()
    return Season.objects.filter(league=lg).order_by('-year')

class SeasonForm(forms.Form):
    league = forms.ModelChoiceField(
        queryset=League.objects.none(),
        required=True,
        label='League',
    )
    course_config = forms.ModelChoiceField(
        queryset=CourseConfig.objects.none(),
        required=True,
        label='Course layout',
    )
    year = forms.IntegerField(label='Year', min_value=2022, max_value=2100)
    weeks = forms.IntegerField(label='Number of Weeks', min_value=1, max_value=52)
    start_date = forms.DateField(label='Start Date', initial=timezone.now)
    START_CHOICES = [
        ("front", "Front Nine"),
        ("back", "Back Nine"),
    ]
    start_with = forms.ChoiceField(label="Start With", choices=START_CHOICES, initial="front")
    playing_skins = forms.BooleanField(
        required=False,
        initial=False,
        label='Playing skins',
    )
    skins_type = forms.ChoiceField(
        label='Skins type',
        choices=Season.SKINS_TYPE_CHOICES,
        initial='GROSS',
    )
    skins_entry_fee = forms.IntegerField(label='Skins entry fee', min_value=0, initial=5)
    playing_games = forms.BooleanField(
        required=False,
        initial=False,
        label='Playing games',
    )
    game_entry_fee = forms.IntegerField(label='Game entry fee', min_value=0, initial=2)
    players_per_team = forms.IntegerField(label='Players per team', min_value=1, max_value=20, initial=2)

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._user = user
        if user and getattr(user, 'is_authenticated', False):
            if user.is_superuser:
                self.fields['league'].queryset = League.objects.all().order_by('name')
            else:
                self.fields['league'].queryset = user.managed_leagues.all().order_by('name')
        else:
            self.fields['league'].queryset = League.objects.none()
        self.fields['course_config'].queryset = CourseConfig.objects.select_related('course').order_by(
            'course__name', 'name'
        )
        for name in ('league', 'course_config', 'year', 'weeks', 'start_date', 'start_with'):
            self.fields[name].widget.attrs.setdefault('class', 'form-control')
        self.fields['start_date'].widget.attrs.setdefault('type', 'date')
        for name in ('skins_type', 'skins_entry_fee', 'game_entry_fee', 'players_per_team'):
            self.fields[name].widget.attrs.setdefault('class', 'form-control')
        self.fields['playing_skins'].widget.attrs.setdefault('class', 'form-check-input')
        self.fields['playing_games'].widget.attrs.setdefault('class', 'form-check-input')

        if not self.is_bound:
            default_league = get_default_league()
            if default_league and self.fields['league'].queryset.filter(pk=default_league.pk).exists():
                self.initial.setdefault('league', default_league.pk)

    def clean(self):
        cleaned = super().clean()
        league = cleaned.get('league')
        user = self._user
        if league and user and getattr(user, 'is_authenticated', False) and not user.is_superuser:
            if not league.managers.filter(pk=user.pk).exists():
                raise ValidationError({'league': 'You can only create seasons for leagues you manage.'})
        return cleaned


class SeasonSettingsForm(forms.ModelForm):
    """Update an existing season’s course layout and gameplay settings."""

    class Meta:
        model = Season
        fields = [
            'course_config',
            'playing_skins',
            'skins_type',
            'skins_entry_fee',
            'playing_games',
            'game_entry_fee',
            'players_per_team',
        ]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._user = user
        self.fields['course_config'].queryset = CourseConfig.objects.select_related('course').order_by(
            'course__name', 'name'
        )
        self.fields['course_config'].required = True
        self.fields['course_config'].widget.attrs.setdefault('class', 'form-select')
        self.fields['skins_type'].widget.attrs.setdefault('class', 'form-select')
        for name in ('skins_entry_fee', 'game_entry_fee', 'players_per_team'):
            self.fields[name].widget.attrs.setdefault('class', 'form-control')
        self.fields['playing_skins'].widget.attrs.setdefault('class', 'form-check-input')
        self.fields['playing_games'].widget.attrs.setdefault('class', 'form-check-input')

    def clean(self):
        cleaned = super().clean()
        league = getattr(self.instance, 'league', None)
        user = self._user
        if league and user and getattr(user, 'is_authenticated', False) and not user.is_superuser:
            if not league.managers.filter(pk=user.pk).exists():
                raise ValidationError('You can only edit seasons for leagues you manage.')
        return cleaned


class LeagueForm(forms.ModelForm):
    class Meta:
        model = League
        fields = ['name']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].widget.attrs.setdefault('class', 'form-control')
        self.fields['name'].widget.attrs.setdefault('placeholder', 'League name')


class CourseManageForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['name', 'city', 'state']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in self.fields:
            self.fields[name].widget.attrs.setdefault('class', 'form-control')


class CourseConfigManageForm(forms.ModelForm):
    class Meta:
        model = CourseConfig
        fields = ['course', 'name', 'effective_start', 'effective_end']
        widgets = {
            'effective_start': forms.DateInput(attrs={'type': 'date'}),
            'effective_end': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['course'].queryset = Course.objects.order_by('name')
        self.fields['course'].widget.attrs.setdefault('class', 'form-select')
        self.fields['name'].widget.attrs.setdefault('class', 'form-control')
        self.fields['name'].widget.attrs.setdefault('placeholder', 'Layout name (e.g. White tees)')
        for fname in ('effective_start', 'effective_end'):
            self.fields[fname].widget.attrs.setdefault('class', 'form-control')


class GolferForm(forms.Form):
    name = forms.CharField(label='Name', max_length=100)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].widget.attrs.update({'autofocus': 'autofocus'})
        
class SubForm(forms.Form):
    absent_golfer = forms.ChoiceField(label='Absent Golfer', required=True, choices=[])
    sub_golfer = forms.ChoiceField(label='Substitute Golfer', required=False, choices=[])
    week = forms.ChoiceField(label='Week', required=True, choices=[])
    no_sub = forms.BooleanField(label='No Sub', required=False)
    
    def __init__(self, absent_golfers, sub_golfers, weeks, *args, season=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['absent_golfer'].choices = [(g.id, g.name) for g in absent_golfers]
        self.fields['sub_golfer'].choices = [(g.id, g.name) for g in sub_golfers]
        self.fields['week'].choices = [(w.id, f"{w} - {'Front' if w.is_front else 'Back'}") for w in weeks]

        next_week = get_next_week(season) if season else get_next_week()
        if next_week:
            self.initial['week'] = next_week.id
    
    # custom validation to ensure that a sub is selected if the no_sub checkbox is not checked
    def clean(self):
        cleaned_data = super().clean()
        no_sub = cleaned_data.get('no_sub')
        sub_golfer = cleaned_data.get('sub_golfer')
        if not no_sub and not sub_golfer:
            raise forms.ValidationError({'no_sub': 'A substitute golfer must be selected if no sub is not checked'})
        if no_sub and sub_golfer:
            raise forms.ValidationError({'no_sub': 'No sub cannot be checked if a substitute golfer is selected'})
        return cleaned_data

class ScheduleForm(forms.Form):
    week = forms.ChoiceField(label='Week', choices=[])
    team1 = forms.ChoiceField(label='Team 1', choices=[])
    team2 = forms.ChoiceField(label='Team 2', choices=[])
    
    def __init__(self, weeks, teams, *args, season=None, **kwargs):
        super().__init__(*args, **kwargs)

        earliest_week = get_earliest_week_without_full_matchups(season)

        # Only set initial when the form is not bound (GET). For POST, preserve submitted data.
        if not self.is_bound:
            if earliest_week:
                self.initial['week'] = earliest_week.id
            elif weeks:
                self.initial['week'] = weeks[0].id
            
        self.fields['week'].choices = [(w.id, f"{w} - {'Front' if w.is_front else 'Back'}") for w in weeks]
        self.fields['team1'].choices = [(t.id, f"{t.golfers.all()[0].name} & {t.golfers.all()[1].name}") for t in teams]
        self.fields['team2'].choices = [(t.id, f"{t.golfers.all()[0].name} & {t.golfers.all()[1].name}") for t in teams]

    # Ensure that the teams are different and have not already been scheduled
    def clean(self):
        cleaned_data = super().clean()
        team1 = cleaned_data.get('team1')
        team2 = cleaned_data.get('team2')
        week = cleaned_data.get('week')

        if not week:
            raise forms.ValidationError('Please select a week before submitting the matchup.')
        if team1 == team2:
            raise forms.ValidationError('Team 1 and Team 2 must be different')
        # Do NOT block if teams are already scheduled; this is handled in the view
        return cleaned_data

class WeekSelectionForm(forms.Form):
    def __init__(self, *args, current_season=None, **kwargs):
        super().__init__(*args, **kwargs)

        cs = current_season or get_current_season()
        if cs:
            self.fields['week'] = forms.ModelChoiceField(
                queryset=Week.objects.filter(season=cs).order_by('number'),
                label="Select Week"
            )
        else:
            self.fields['week'] = forms.ModelChoiceField(
                queryset=Week.objects.all().order_by('number'),
                label="Select Week"
            )

        next_week = get_next_week(cs) if cs else get_next_week()
        if next_week:
            self.initial['week'] = next_week
        
class TeamForm(forms.Form):
    season = forms.ModelChoiceField(queryset=Season.objects.all().order_by('-year'), label="Select Season")
    
    golfer1 = forms.ModelChoiceField(queryset=Golfer.objects.all(), label="Select Golfer")
    golfer2 = forms.ModelChoiceField(queryset=Golfer.objects.all(), label="Select Golfer")
    
    def __init__(self, *args, league=None, **kwargs):
        super().__init__(*args, **kwargs)
        lg = league or get_default_league()
        if lg:
            self.fields['season'].queryset = Season.objects.filter(league=lg).order_by('-year')
            gq = Golfer.objects.filter(leagues=lg).order_by('name')
            self.fields['golfer1'].queryset = gq
            self.fields['golfer2'].queryset = gq
        else:
            self.fields['season'].queryset = Season.objects.none()
            self.fields['golfer1'].queryset = Golfer.objects.none()
            self.fields['golfer2'].queryset = Golfer.objects.none()
        self.fields['golfer1'].empty_label = None
        self.fields['golfer2'].empty_label = None

class SeasonSelectForm(forms.Form):
    year = forms.ModelChoiceField(queryset=Season.objects.none(), required=True, label='Select Season')
    
    def __init__(self, *args, all_seasons=False, **kwargs):
        super().__init__(*args, **kwargs)
        if all_seasons:
            self.fields['year'].queryset = Season.objects.select_related('league', 'course_config').order_by(
                '-year', 'league__name'
            )
            self.fields['year'].label_from_instance = lambda obj: f'{obj.league.name} — {obj.year}'
        else:
            self.fields['year'].queryset = _seasons_for_default_league()
        
class HoleForm(forms.Form):
    par = forms.IntegerField(label='Par', required=True, min_value=3, max_value=5)
    handicap = forms.IntegerField(label='Handicap', required=True, min_value=1, max_value=18)
    yards = forms.IntegerField(label='Yards', required=True, min_value=50, max_value=600)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


def hole_formset_initial_for_config(course_config):
    """Build 18 dicts for ``HoleFormSet`` ``initial=`` — holes not yet stored use empty dicts."""
    by_num = {h.number: h for h in Hole.objects.filter(config=course_config).order_by('number')}
    initial = []
    for n in range(1, 19):
        h = by_num.get(n)
        if h:
            initial.append({'par': h.par, 'handicap': h.handicap, 'yards': h.yards})
        else:
            initial.append({})
    return initial


class SkinEntryForm(forms.Form):
    week = forms.ModelChoiceField(
        queryset=Week.objects.all().order_by('-date'), 
        label='Week',
        required=True
    )
    golfers = forms.ModelMultipleChoiceField(
        queryset=Golfer.objects.all().order_by('name'),
        label='Golfers in Skins',
        required=True,
        widget=forms.CheckboxSelectMultiple
    )
    
    def __init__(self, *args, current_season=None, **kwargs):
        super().__init__(*args, **kwargs)
        cs = current_season or get_current_season()
        if cs:
            self.fields['week'].queryset = Week.objects.filter(season=cs).order_by('-date')

            next_week = get_next_week(cs)
            if next_week:
                self.initial['week'] = next_week.id
        week = None
        # Priority: POST data > initial['week']
        if self.data.get('week'):
            try:
                week = Week.objects.get(pk=self.data.get('week'))
            except Exception:
                week = None
        elif self.initial.get('week'):
            try:
                week = Week.objects.get(pk=self.initial['week'])
            except Exception:
                week = None
        if week:
            playing_golfers = get_playing_golfers_for_week(week)
            self.fields['golfers'].queryset = Golfer.objects.filter(id__in=[g.id for g in playing_golfers]).order_by('name')
        else:
            self.fields['golfers'].queryset = Golfer.objects.none()
    
    def clean(self):
        cleaned_data = super().clean()
        week = cleaned_data.get('week')
        golfers = cleaned_data.get('golfers')
        
        if week and golfers:
            # Get golfers who are actually playing this week (including subs)
            playing_golfers = set()
            
            # Get all teams for the season
            teams = Team.objects.filter(season=week.season)
            
            for team in teams:
                team_golfers = team.golfers.all()
                for golfer in team_golfers:
                    # Check if golfer is playing (not absent or has a sub)
                    sub = Sub.objects.filter(week=week, absent_golfer=golfer).first()
                    if not sub or (sub and sub.sub_golfer):
                        # Golfer is playing (either directly or via sub)
                        if sub and sub.sub_golfer:
                            playing_golfers.add(sub.sub_golfer)  # Add the sub
                        else:
                            playing_golfers.add(golfer)  # Add the original golfer
            
            # Check if all selected golfers are actually playing
            non_playing = set(golfers) - playing_golfers
            if non_playing:
                golfer_names = [g.name for g in non_playing]
                raise forms.ValidationError(f"The following golfers are not playing in Week {week.number}: {', '.join(golfer_names)}")
        
        return cleaned_data

class CreateGameForm(forms.Form):
    name = forms.CharField(max_length=100, widget=forms.TextInput(attrs={'class': 'form-control'}))
    desc = forms.CharField(max_length=200, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    week = forms.ModelChoiceField(
        queryset=Week.objects.none(),
        empty_label="Select a week",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    def __init__(self, *args, current_season=None, **kwargs):
        super().__init__(*args, **kwargs)
        cs = current_season or get_current_season()
        if cs:
            self.fields['week'].queryset = Week.objects.filter(season=cs).order_by('-number')

            next_week = get_next_week(cs)
            if next_week:
                self.initial['week'] = next_week

class GameEntryForm(forms.Form):
    week = forms.ModelChoiceField(
        queryset=Week.objects.none(),
        empty_label="Select a week",
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'game-week-select'})
    )
    golfers = forms.ModelMultipleChoiceField(
        queryset=Golfer.objects.none(),
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'golfer-checkbox'}),
        required=False
    )
    
    def __init__(self, *args, current_season=None, **kwargs):
        initial_week = kwargs.pop('initial_week', None)
        super().__init__(*args, **kwargs)
        cs = current_season or get_current_season()
        if cs:
            self.fields['week'].queryset = Week.objects.filter(season=cs).order_by('-number')
        week = None
        if self.data.get('week'):
            try:
                week = Week.objects.get(pk=self.data.get('week'))
            except Exception:
                week = None
        elif initial_week:
            week = initial_week
        elif self.initial.get('week'):
            try:
                week = Week.objects.get(pk=self.initial['week'])
            except Exception:
                week = None
        else:
            next_week = get_next_week(cs) if cs else get_next_week()
            if next_week:
                self.initial['week'] = next_week.id
                week = next_week
        if week:
            playing_golfers = get_playing_golfers_for_week(week)
            self.fields['golfers'].queryset = Golfer.objects.filter(id__in=[g.id for g in playing_golfers]).order_by('name')
        else:
            self.fields['golfers'].queryset = Golfer.objects.none()

    def clean(self):
        cleaned_data = super().clean()
        week = cleaned_data.get('week')
        golfers = cleaned_data.get('golfers')

        if week and golfers:
            # Check if there's a game for this week
            game = Game.objects.filter(week=week).first()
            if not game:
                raise forms.ValidationError(f"No game has been created for Week {week.number}. Please create a game first.")
            
            # Get golfers who are actually playing this week (including subs)
            playing_golfers = set()
            
            # Get all teams for the season
            teams = Team.objects.filter(season=week.season)
            
            for team in teams:
                team_golfers = team.golfers.all()
                for golfer in team_golfers:
                    # Check if golfer is playing (not absent or has a sub)
                    sub = Sub.objects.filter(week=week, absent_golfer=golfer).first()
                    if not sub or (sub and sub.sub_golfer):
                        # Golfer is playing (either directly or via sub)
                        if sub and sub.sub_golfer:
                            playing_golfers.add(sub.sub_golfer)  # Add the sub
                        else:
                            playing_golfers.add(golfer)  # Add the original golfer
            
            # Check if all selected golfers are actually playing
            non_playing = set(golfers) - playing_golfers
            if non_playing:
                golfer_names = [g.name for g in non_playing]
                raise forms.ValidationError(f"The following golfers are not playing in Week {week.number}: {', '.join(golfer_names)}")
        
        return cleaned_data

class GameWinnerForm(forms.Form):
    week = forms.ModelChoiceField(
        queryset=Week.objects.none(),
        empty_label="Select a week",
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'winner-week-select'})
    )
    winner = forms.ModelChoiceField(
        queryset=Golfer.objects.none(),
        empty_label="Select a winner",
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'winner-select'})
    )
    
    def __init__(self, *args, current_season=None, **kwargs):
        initial_week = kwargs.pop('initial_week', None)
        super().__init__(*args, **kwargs)
        cs = current_season or get_current_season()
        if cs:
            self.fields['week'].queryset = Week.objects.filter(season=cs).order_by('-number')
        week = None
        if self.data.get('week'):
            try:
                week = Week.objects.get(pk=self.data.get('week'))
            except Exception:
                week = None
        elif initial_week:
            week = initial_week
        else:
            next_week = get_next_week(cs) if cs else get_next_week()
            if next_week:
                self.initial['week'] = next_week
                week = next_week
        if week:
            # Only golfers who have entries for this week/game
            game = Game.objects.filter(week=week).first()
            if game:
                entry_golfers = GameEntry.objects.filter(week=week, game=game).values_list('golfer', flat=True)
                self.fields['winner'].queryset = Golfer.objects.filter(id__in=entry_golfers).order_by('name')
            else:
                self.fields['winner'].queryset = Golfer.objects.none()
        else:
            self.fields['winner'].queryset = Golfer.objects.none()