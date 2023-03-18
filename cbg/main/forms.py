from django import forms
from django.db.models import Q
from main.models import *
from main.helper import *

class RoundForm(forms.Form):
    golfer = forms.ModelChoiceField(queryset=Golfer.objects.all(), label='Golfer', widget=forms.Select(attrs={'class' : 'form-control'}))
    hole1 = forms.IntegerField(label='Hole 1', max_value=10, min_value=1, widget=forms.NumberInput(attrs={'class' : 'form-control'}))
    hole2 = forms.IntegerField(label='Hole 2', max_value=10, min_value=1, widget=forms.NumberInput(attrs={'class' : 'form-control'}))
    hole3 = forms.IntegerField(label='Hole 3', max_value=10, min_value=1, widget=forms.NumberInput(attrs={'class' : 'form-control'}))
    hole4 = forms.IntegerField(label='Hole 4', max_value=10, min_value=1, widget=forms.NumberInput(attrs={'class' : 'form-control'}))
    hole5 = forms.IntegerField(label='Hole 5', max_value=10, min_value=1, widget=forms.NumberInput(attrs={'class' : 'form-control'}))
    hole6 = forms.IntegerField(label='Hole 6', max_value=10, min_value=1, widget=forms.NumberInput(attrs={'class' : 'form-control'}))
    hole7 = forms.IntegerField(label='Hole 7', max_value=10, min_value=1, widget=forms.NumberInput(attrs={'class' : 'form-control'}))
    hole8 = forms.IntegerField(label='Hole 8', max_value=10, min_value=1, widget=forms.NumberInput(attrs={'class' : 'form-control'}))
    hole9 = forms.IntegerField(label='Hole 9', max_value=10, min_value=1, widget=forms.NumberInput(attrs={'class' : 'form-control'}))
    week = forms.ModelChoiceField(queryset=Week.objects.all(), label='Week', widget=forms.Select(attrs={'class' : 'form-control'}))
    season = forms.ModelChoiceField(queryset=Season.objects.all(), label='Season', widget=forms.Select(attrs={'class' : 'form-control'}))
    self_sub = forms.BooleanField(label='Playing With No Partner', required=False, widget=forms.CheckboxInput())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['week'].queryset = Week.objects.filter(season__year=self.fields['year'].initial)
        self.fields['week'].label_from_instance = self.label_from_week_instance
