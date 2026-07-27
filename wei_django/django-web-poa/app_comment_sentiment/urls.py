from django.urls import path
from . import views

app_name = "app_comment_sentiment"
urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("scheduler/", views.scheduler, name="scheduler"),  # 新增的排程頁面
    path("django-command-scheduling-guide/", views.django_command_scheduling_guide, name="django_command_scheduling_guide"),
    path("api/data/", views.api_data, name="api_data"),
    path("api/scheduler/status/", views.api_scheduler_status, name="api_scheduler_status"),
    path("api/scheduler/start/", views.api_scheduler_start, name="api_scheduler_start"),
    path("api/scheduler/stop/", views.api_scheduler_stop, name="api_scheduler_stop"),
    path("api/run-task/", views.api_run_task, name="api_run_task"),
    path("api/scheduler/history/", views.api_scheduler_history, name="api_scheduler_history"),  # 新增的歷史紀錄API
]