from django.urls import path
from . import views

app_name = 'app_rag_agent'

urlpatterns = [
    path('', views.chat_view, name='chat_view'),
    path('clear/', views.clear_chat, name='clear_chat'),
    path('intro/', views.app_intro, name='app_intro'),
]
