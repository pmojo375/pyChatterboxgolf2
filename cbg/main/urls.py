from django.urls import path, register_converter, include
from . import views
from .api import get_matchup_data, get_playing_golfers, get_games_for_week, get_games_by_week, get_game_entries, get_week_matchups

# Custom path converter for 4-digit years
class YearConverter:
    regex = r'[12]\d{3}'  # Years 1000-2999
    
    def to_python(self, value):
        return int(value)
    
    def to_url(self, value):
        return str(value)

register_converter(YearConverter, 'year')

urlpatterns = [
    path('', views.main, name='main'),
    # League-prefixed routes (must be before bare <year> so slugs are not parsed as years)
    path('<slug:league_slug>/historics/', views.historics, name='historics_with_league'),
    path('<slug:league_slug>/<year:year>/', views.main, name='main_with_league_year'),
    path('<slug:league_slug>/<year:year>/<int:week>/', views.scorecards, name='scorecards_with_league_year'),
    path('<slug:league_slug>/<year:year>/stats/<int:golfer_id>/', views.golfer_stats, name='golfer_stats_with_league_year'),
    path('<slug:league_slug>/<year:year>/sub_stats/', views.sub_stats, name='sub_stats_with_league_year'),
    path('<slug:league_slug>/<year:year>/sub_stats/<int:golfer_id>/', views.sub_stats, name='sub_stats_detail_with_league_year'),
    path('<slug:league_slug>/<year:year>/league_stats/', views.league_stats, name='league_stats_with_league_year'),
    # League-scoped management (year = season calendar year)
    path('<slug:league_slug>/<year:year>/add_round/', views.add_scores, name='add_round_with_league_year'),
    path('<slug:league_slug>/<year:year>/add_golfer/', views.add_golfer, name='add_golfer_with_league_year'),
    path('<slug:league_slug>/<year:year>/add_sub/', views.add_sub, name='add_sub_with_league_year'),
    path('<slug:league_slug>/<year:year>/enter_schedule/', views.enter_schedule, name='enter_schedule_with_league_year'),
    path('<slug:league_slug>/<year:year>/blank_scorecards/', views.blank_scorecards, name='blank_scorecards_with_league_year'),
    path('<slug:league_slug>/<year:year>/set_rainout/', views.set_rainout, name='set_rainout_with_league_year'),
    path('<slug:league_slug>/<year:year>/create_season/', views.create_season, name='create_season_with_league_year'),
    path('<slug:league_slug>/<year:year>/edit_season/', views.edit_season, name='edit_season_with_league_year'),
    path('<slug:league_slug>/<year:year>/create_team/', views.create_team, name='create_team_with_league_year'),
    path('<slug:league_slug>/<year:year>/generate_rounds/', views.generate_rounds_page, name='generate_rounds_with_league_year'),
    path('<slug:league_slug>/<year:year>/manage_skins/', views.manage_skins, name='manage_skins_with_league_year'),
    path('<slug:league_slug>/<year:year>/manage_games/', views.manage_games, name='manage_games_with_league_year'),
    path('<slug:league_slug>/<year:year>/manage_weeks/', views.manage_weeks, name='manage_weeks_with_league_year'),
    path('<year:year>/', views.main, name='main_with_year'),
    path('add_round', views.add_scores, name='add_round'),
    path('add_golfer', views.add_golfer, name='add_golfer'),
    path('add_sub', views.add_sub, name='add_sub'),
    path('enter_schedule', views.enter_schedule, name='enter_schedule'),
    path('blank_scorecards/', views.blank_scorecards, name="blank_scorecards"),
    path('stats/<int:golfer_id>/', views.golfer_stats, name="golfer_stats"),
    path('sub_stats/', views.sub_stats, name="sub_stats"),
    path('sub_stats/<int:golfer_id>/', views.sub_stats, name="sub_stats_detail"),
    path('league_stats/', views.league_stats, name="league_stats"),
    path('set_rainout', views.set_rainout, name='set_rainout'),
    path('create_season', views.create_season, name='create_season'),
    path('edit_season/<int:season_id>/', views.edit_season, name='edit_season'),
    path('leagues/add/', views.add_league, name='add_league'),
    path('create_team', views.create_team, name='create_team'),
    path('set_holes', views.set_holes, name='set_holes'),
    path('courses/', views.manage_courses, name='manage_courses'),
    path('generate_rounds', views.generate_rounds_page, name='generate_rounds'),
    path('manage_skins', views.manage_skins, name='manage_skins'),
    path('manage_games', views.manage_games, name='manage_games'),
    path('api/get_matchup/<int:matchup_id>/', get_matchup_data, name='get_matchup_data'),
    path('api/get_playing_golfers/<int:week_id>/', get_playing_golfers, name='get_playing_golfers'),
    path('api/get_games_for_week/<int:week_id>/', get_games_for_week, name='get_games_for_week'),
    path('api/get_games_by_week/<int:week_id>/', get_games_by_week, name='get_games_by_week'),
    path('api/get_game_entries/<int:week_id>/<int:game_id>/', get_game_entries, name='get_game_entries'),
    path('api/get_week_matchups/', get_week_matchups, name='get_week_matchups'),
    
    # New URL patterns with year parameter (4-digit years only) - must come before week patterns
    path('<year:year>/<int:week>/', views.scorecards, name='scorecards_with_year'),
    path('<year:year>/stats/<int:golfer_id>/', views.golfer_stats, name="golfer_stats_with_year"),
    path('<year:year>/sub_stats/', views.sub_stats, name="sub_stats_with_year"),
    path('<year:year>/sub_stats/<int:golfer_id>/', views.sub_stats, name="sub_stats_detail_with_year"),
    path('<year:year>/league_stats/', views.league_stats, name="league_stats_with_year"),
    path('historics/', views.historics, name='historics'),
    
    # Week patterns (must come after year patterns to avoid conflicts)
    path('<int:week>/', views.scorecards, name="scorecards"),
    path('manage_weeks/', views.manage_weeks, name='manage_weeks'),
    path("accounts/", include("django.contrib.auth.urls")),
]