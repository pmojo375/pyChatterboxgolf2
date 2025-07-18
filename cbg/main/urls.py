from django.urls import path
from . import views
from .api import get_matchup_data, get_playing_golfers, get_games_for_week, get_games_by_week, get_game_entries


urlpatterns = [
    path('', views.main, name='main'),
    path('add_round', views.add_scores, name='add_round'),
    path('add_golfer', views.add_golfer, name='add_golfer'),
    path('add_sub', views.add_sub, name='add_sub'),
    path('enter_schedule', views.enter_schedule, name='enter_schedule'),
    path('<int:week>/', views.scorecards, name="scorecards"),
    path('blank_scorecards/', views.blank_scorecards, name="blank_scorecards"),
    path('stats/<int:golfer_id>/', views.golfer_stats, name="golfer_stats"),
    path('sub_stats/', views.sub_stats, name="sub_stats"),
    path('sub_stats/<int:golfer_id>/', views.sub_stats, name="sub_stats_detail"),
    path('league_stats/', views.league_stats, name="league_stats"),
    path('set_rainout', views.set_rainout, name='set_rainout'),
    path('create_season', views.create_season, name='create_season'),
    path('create_team', views.create_team, name='create_team'),
    path('set_holes', views.set_holes, name='set_holes'),
    path('generate_rounds', views.generate_rounds_page, name='generate_rounds'),
    path('manage_skins', views.manage_skins, name='manage_skins'),
    path('manage_games', views.manage_games, name='manage_games'),
    path('api/get_matchup/<int:matchup_id>/', get_matchup_data, name='get_matchup_data'),
    path('api/get_playing_golfers/<int:week_id>/', get_playing_golfers, name='get_playing_golfers'),
    path('api/get_games_for_week/<int:week_id>/', get_games_for_week, name='get_games_for_week'),
    path('api/get_games_by_week/<int:week_id>/', get_games_by_week, name='get_games_by_week'),
    path('api/get_game_entries/<int:week_id>/<int:game_id>/', get_game_entries, name='get_game_entries'),
    
]
