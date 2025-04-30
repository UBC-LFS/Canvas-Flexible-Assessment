from django.urls import path
from . import views

app_name = "due_dates"

urlpatterns = [
    path("<int:course_id>/", views.DueDatesHome.as_view(), name='due_dates_home'),
    path("<int:course_id>/students", views.DueDatesStudents.as_view(), name='due_dates_students'),
    path("<int:course_id>/quizzes", views.DueDatesQuizzes.as_view(), name='due_dates_quizzes'),
]