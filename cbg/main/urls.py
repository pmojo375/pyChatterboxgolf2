from django.urls import path
from . import views


urlpatterns = [
    path('', views.main, name='main'),
    path('add_round', views.add_scores, name='add_round'),
    path('add_golfer', views.add_golfer, name='add_golfer'),
    path('add_sub', views.add_sub, name='add_sub'),
    path('enter_schedule', views.enter_schedule, name='enter_schedule'),
    path('<int:week>/', views.scorecards, name="scorecards"),
    path('stats/<int:golfer_id>/', views.golfer_stats, name="golfer_stats"),
    path('manage_weeks', views.manage_weeks, name='manage_weeks'),
    path('create_season', views.create_season, name='create_season')
]
