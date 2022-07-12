
from django.urls import path

from . import views

app_name = 'student'
urlpatterns = [
    path('<int:course_id>/', views.StudentHome.as_view(), name='student_home'),
    path(
        '<int:course_id>/form/',
        views.StudentAssessmentView.as_view(),
        name='student_form')
]
