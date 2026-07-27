from django.urls import path
from . import views

app_name = 'app_movies'

urlpatterns = [
    path('', views.home, name='home'),
    path('api_get_movie_data/', views.api_get_movie_data, name='api_get_movie_data'),
]
