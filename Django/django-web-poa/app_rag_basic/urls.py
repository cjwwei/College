from django.urls import path
from . import views

app_name = "app_rag_basic"

urlpatterns = [
    path("", views.rag_demo_view, name="chat_view"),
]
