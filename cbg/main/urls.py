from django.urls import path
from . import views


urlpatterns = [
    path('', views.main, name='main'),
    path('add_round', views.add_scores, name='add_round'),
    path('add_golfer', views.add_golfer, name='add_golfer'),
    path('add_sub', views.add_sub, name='add_sub'),
    path('enter_schedule', views.enter_schedule, name='enter_schedule'),
    path('<int:week>/', views.scorecards, name="scorecards"),
]
