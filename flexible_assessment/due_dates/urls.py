from django.urls import path
from . import views

app_name = "due_dates"

urlpatterns = [
    path("<int:course_id>/", views.DueDatesHome.as_view(), name='due_dates_home'),
]