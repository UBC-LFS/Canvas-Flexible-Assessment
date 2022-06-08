
from django.urls import path

from . import views

app_name = 'student'
urlpatterns = [
    path('student/', views.student_home, name='student_home'),
    path(
        'student/form/',
        views.StudentFormView.as_view(),
        name='student_form')
]