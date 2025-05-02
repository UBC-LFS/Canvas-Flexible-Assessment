from django.urls import path
from . import views

app_name = "accommodations"
urlpatterns = [
    path("<int:course_id>/", views.AccommodationsHome.as_view(), name="accommodations_home"),
    path("<int:course_id>/quizzes", views.quizzes, name="accommodations_quizzes"),

]