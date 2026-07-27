from django.shortcuts import render
from django.http import JsonResponse
import pandas as pd
import os

def load_data():
    file_path = os.path.join('app_movies', 'dataset', 'douban_movies.csv')
    df = pd.read_csv(file_path)
    # Get top 20 movies by rating
    df = df.sort_values(by='電影評分', ascending=False).head(20)
    return df

def home(request):
    df = load_data()
    movies = df['電影名稱'].tolist()
    ratings = df['電影評分'].tolist()
    context = {
        'movies': movies,
        'ratings': ratings,
    }
    return render(request, 'app_movies/home.html', context)

def api_get_movie_data(request):
    df = load_data()
    data = {
        'labels': df['電影名稱'].tolist(),
        'values': df['電影評分'].tolist(),
    }
    return JsonResponse(data)
