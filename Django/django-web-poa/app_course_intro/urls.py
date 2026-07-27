    
from django.urls import path
from django.views.generic import TemplateView   

app_name="app_course_intro"

urlpatterns = [
    # course introduction
    path('course_intro', TemplateView.as_view(template_name='app_course_intro/course-introduction.html'), name='course_introduction'),

    # api introduction
    path('api_intro', TemplateView.as_view(template_name='app_course_intro/api-introduction.html'), name='api_introduction'),
]

