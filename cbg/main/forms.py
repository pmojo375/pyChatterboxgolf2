from django import forms
from django.db.models import Q
from main.models import *
from main.helper import *
from django.utils import timezone
from main.helper import get_playing_golfers_for_week, get_earliest_week_without_full_matchups, get_next_week

class SeasonForm(forms.Form):
    year = forms.IntegerField(label='Year', min_value=2022, max_value=2100)
    weeks = forms.IntegerField(label='Number of Weeks', min_value=1, max_value=52)
    start_date = forms.DateField(label='Start Date', initial=timezone.now)

class ScoresForm(forms.Form):
    golfer = forms.ChoiceField(label='Golfer', choices=[])
    week = forms.ChoiceField(label='Week', choices=[])

    # Create fields for each hole
    for hole in range(1, 10):
        locals()[f'hole{hole}'] = forms.IntegerField(
            label=f'Hole {hole}', 
            min_value=1, 
            max_value=10, 
            required=True
        )

    def __init__(self, golfers, weeks, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['golfer'].choices = [(g.id, g.name) for g in golfers]
        self.fields['week'].choices = [(w.id, f"{w} - {'Front' if w.is_front else 'Back'}") for w in weeks]
        self.initial['week'] = weeks[0].id if weeks else None
        
class RoundForm(forms.Form):
    matchup = forms.ChoiceField(label='Matchup', choices=[])
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # get the next week with no scores entered
        week = get_next_week()
        
        # get all matchups for the week
        self.matchups = Matchup.objects.filter(week=week)
        
        # get golfers from matchups accounting for subs
        self.golfer_data = []
        matchup_golfers = []
        
        # Create fields for each of the 9 holes for each golfer
        for hole in range(1, 10):
            for golfer_num in range(1, 5):  # Assume max of 4 golfers
                field_name = f'hole{hole}_{golfer_num}'
                
                self.fields[field_name] = forms.IntegerField(
                    label=f'Hole {hole} - Golfer {golfer_num}', 
                    min_value=1, 
                    max_value=10, 
                    required=True
                )
        
        # iterate through each matchup and get all golfers and their handicaps accounting for subs
        for _matchup in self.matchups:
            
            team1 = []
            team2 = []
            
            # iterate through the teams in the matchup
            for team in _matchup.teams.all():
                
                _golfers = []
                
                # iterate though the teams golfers
                for golfer in team.golfers.all():
                    
                    if Sub.objects.filter(week=_matchup.week, absent_golfer=golfer).exists():
                        sub = Sub.objects.filter(week=_matchup.week, absent_golfer=golfer).first()
                        
                        # if the golfer has no sub, get their handicap
                        if sub.no_sub:
                            partner = [g for g in team.golfers.all() if g != golfer][0]
                            handicap = get_hcp(partner, week)
                            _golfers.append({'golfer': partner, 'handicap': handicap})
                        else:
                            handicap = get_hcp(sub.sub_golfer, week)
                            _golfers.append({'golfer': sub.sub_golfer, 'handicap': handicap})

                    else:
                        handicap = get_hcp(golfer, week)
                        _golfers.append({'golfer': golfer, 'handicap': handicap})
                        
                if team1 == []:
                    team1 = _golfers
                else:
                    team2 = _golfers

            # determine which golfer on each team has the better handicap and put them as the first two in the list
            if team1[0]['handicap'] <= team1[1]['handicap']:
                if team2[0]['handicap'] <= team2[1]['handicap']:
                    golfers = [team1[0]['golfer'], team2[0]['golfer'], team1[1]['golfer'], team2[1]['golfer']]
                else:
                    golfers = [team1[0]['golfer'], team2[1]['golfer'], team1[1]['golfer'], team2[0]['golfer']]
            else:
                if team2[0]['handicap'] <= team2[1]['handicap']:
                    golfers = [team1[1]['golfer'], team2[0]['golfer'], team1[0]['golfer'], team2[1]['golfer']]
                else:
                    golfers = [team1[1]['golfer'], team2[1]['golfer'], team1[0]['golfer'], team2[0]['golfer']]

            matchup_golfers.append(golfers)

        # I now have each matchups golfers with subs accounted for
        _matchups = []
        
        for i, golfers in enumerate(matchup_golfers):
            display_text = f"{golfers[0].name} vs. {golfers[1].name} - {golfers[2].name} vs. {golfers[3].name}"
                
            _matchups.append((i, display_text))
            self.golfer_data.append([[g.name, g.id, get_hcp(g, week)] for g in golfers])
            
        self.fields['matchup'].choices = _matchups
             
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
    
    def __init__(self, absent_golfers, sub_golfers, weeks, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['absent_golfer'].choices = [(g.id, g.name) for g in absent_golfers]
        self.fields['sub_golfer'].choices = [(g.id, g.name) for g in sub_golfers]
        self.fields['week'].choices = [(w.id, f"{w} - {'Front' if w.is_front else 'Back'}") for w in weeks]
        
        # Find the next week without scores entered and set it as initial
        next_week = get_next_week()
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
    
    def __init__(self, weeks, teams, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Find the earliest week without full matchups
        earliest_week = get_earliest_week_without_full_matchups()
        
        # Set initial week to the earliest week without full matchups, or first week if none found
        if earliest_week:
            self.initial['week'] = earliest_week.id
        else:
            self.initial['week'] = weeks[0].id if weeks else None
            
        self.fields['week'].choices = [(w.id, f"{w} - {'Front' if w.is_front else 'Back'}") for w in weeks]
        self.fields['team1'].choices = [(t.id, f"{t.golfers.all()[0].name} & {t.golfers.all()[1].name}") for t in teams]
        self.fields['team2'].choices = [(t.id, f"{t.golfers.all()[0].name} & {t.golfers.all()[1].name}") for t in teams]

    # Ensure that the teams are different and have not already been scheduled
    def clean(self):
        cleaned_data = super().clean()
        team1 = cleaned_data.get('team1')
        team2 = cleaned_data.get('team2')
        week = cleaned_data.get('week')
        if team1 == team2:
            raise forms.ValidationError('Team 1 and Team 2 must be different')
        if Matchup.objects.filter(week_id=week).filter(Q(teams__id=team1) | Q(teams__id=team2)).exists():
            raise forms.ValidationError('Teams have already been scheduled for this week')
        return cleaned_data

class WeekSelectionForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        current_season = get_current_season()
        if current_season:
            self.fields['week'] = forms.ModelChoiceField(
                queryset=Week.objects.filter(season=current_season).order_by('number'), 
                label="Select Week"
            )
        else:
            self.fields['week'] = forms.ModelChoiceField(
                queryset=Week.objects.all().order_by('number'), 
                label="Select Week"
            )
        
        # Find the next week without scores entered and set it as initial
        next_week = get_next_week()
        if next_week:
            self.initial['week'] = next_week
        
class TeamForm(forms.Form):
    season = forms.ModelChoiceField(queryset=Season.objects.all().order_by('-year'), label="Select Season")
    
    golfer1 = forms.ModelChoiceField(queryset=Golfer.objects.all(), label="Select Golfer")
    golfer2 = forms.ModelChoiceField(queryset=Golfer.objects.all(), label="Select Golfer")
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['golfer1'].empty_label = None
        self.fields['golfer2'].empty_label = None

class SeasonSelectForm(forms.Form):
    year = forms.ModelChoiceField(queryset=Season.objects.all().order_by('-year'), required=True, label='Select Season')
    
    class Meta:
        model = Season
        fields = ['year']
        
class HoleForm(forms.Form):
    par = forms.IntegerField(label='Par', required=True, min_value=3, max_value=5)
    handicap = forms.IntegerField(label='Handicap', required=True, min_value=1, max_value=18)
    yards = forms.IntegerField(label='Yards', required=True, min_value=50, max_value=600)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set current season's weeks as default
        current_season = Season.objects.order_by('-year').first()
        if current_season:
            self.fields['week'].queryset = Week.objects.filter(season=current_season).order_by('-date')
            
            # Find the next week (active week that needs scores) and set it as initial
            next_week = get_next_week()
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
            self.fields['golfer'].queryset = Golfer.objects.none()
    
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
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Get current season weeks
        current_season = Season.objects.order_by('-year').first()
        if current_season:
            self.fields['week'].queryset = Week.objects.filter(season=current_season).order_by('-number')
            
            # Find the next week (active week that needs scores) and set it as initial
            next_week = get_next_week()
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
    
    def __init__(self, *args, **kwargs):
        initial_week = kwargs.pop('initial_week', None)
        super().__init__(*args, **kwargs)
        current_season = Season.objects.order_by('-year').first()
        if current_season:
            self.fields['week'].queryset = Week.objects.filter(season=current_season).order_by('-number')
        week = None
        # Priority: POST data > initial_week > initial['week']
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
            # Find the next week (active week that needs scores) and set it as initial
            next_week = get_next_week()
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
    
    def __init__(self, *args, **kwargs):
        initial_week = kwargs.pop('initial_week', None)
        super().__init__(*args, **kwargs)
        current_season = Season.objects.order_by('-year').first()
        if current_season:
            self.fields['week'].queryset = Week.objects.filter(season=current_season).order_by('-number')
        week = None
        if self.data.get('week'):
            try:
                week = Week.objects.get(pk=self.data.get('week'))
            except Exception:
                week = None
        elif initial_week:
            week = initial_week
        else:
            # Find the next week (active week that needs scores) and set it as initial
            next_week = get_next_week()
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