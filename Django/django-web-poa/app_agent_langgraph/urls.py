from django.urls import path
from . import views

app_name = 'app_agent_langgraph'

urlpatterns = [
    path('chat/', views.chat_view, name='chat_view'),
]
