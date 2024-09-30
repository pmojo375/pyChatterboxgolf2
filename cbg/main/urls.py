from django.urls import path
from . import views
from .api import get_matchup_data


urlpatterns = [
    path('', views.main, name='main'),
    path('add_round', views.add_scores, name='add_round'),
    path('add_golfer', views.add_golfer, name='add_golfer'),
    path('add_sub', views.add_sub, name='add_sub'),
    path('enter_schedule', views.enter_schedule, name='enter_schedule'),
    path('<int:week>/', views.scorecards, name="scorecards"),
    path('stats/<int:golfer_id>/', views.golfer_stats, name="golfer_stats"),
    path('set_rainout', views.set_rainout, name='set_rainout'),
    path('create_season', views.create_season, name='create_season'),
    path('create_team', views.create_team, name='create_team'),
    path('set_holes', views.set_holes, name='set_holes'),
    path('api/get_matchup/<int:matchup_id>/', get_matchup_data, name='get_matchup_data'),
    
]
