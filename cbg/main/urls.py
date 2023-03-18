from django.urls import path
from . import views

urlpatterns = [
    path('', views.main, name='main'),
    path('add_round', views.add_round, name='add_round'),
]