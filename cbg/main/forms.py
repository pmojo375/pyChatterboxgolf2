from django import forms
from django.db.models import Q
from main.models import *
from main.helper import *
from django.utils import timezone

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
        
class GolferForm(forms.Form):
    name = forms.CharField(label='Name', max_length=100)
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['name'].widget.attrs.update({'autofocus': 'autofocus'})
        
class SubForm(forms.Form):
    absent_golfer = forms.ChoiceField(label='Absent Golfer', choices=[])
    sub_golfer = forms.ChoiceField(label='Substitute Golfer', choices=[])
    week = forms.ChoiceField(label='Week', choices=[])
    
    def __init__(self, absent_golfers, sub_golfers, weeks, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial['week'] = weeks[0].id if weeks else None
        self.fields['absent_golfer'].choices = [(g.id, g.name) for g in absent_golfers]
        self.fields['sub_golfer'].choices = [(g.id, g.name) for g in sub_golfers]
        self.fields['week'].choices = [(w.id, f"{w} - {'Front' if w.is_front else 'Back'}") for w in weeks]

class ScheduleForm(forms.Form):
    week = forms.ChoiceField(label='Week', choices=[])
    team1 = forms.ChoiceField(label='Team 1', choices=[])
    team2 = forms.ChoiceField(label='Team 2', choices=[])
    
    def __init__(self, weeks, teams, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
        