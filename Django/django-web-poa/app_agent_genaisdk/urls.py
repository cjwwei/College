from django.urls import path
from app_agent_genaisdk import views

app_name = 'app_agent_genaisdk'

urlpatterns = [
    path('chat/', views.chat_view, name='chat_view'),
    path('clear-history/', views.clear_history, name='clear_history'),
    path('introduction/', views.poa_agent_introduction, name='poa_agent_introduction'),
]
