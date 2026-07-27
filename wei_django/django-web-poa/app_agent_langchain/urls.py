from django.urls import path
from app_agent_langchain import views

app_name = 'app_agent_langchain'

urlpatterns = [
    path('chat/', views.chat_view, name='chat_view'),
]
