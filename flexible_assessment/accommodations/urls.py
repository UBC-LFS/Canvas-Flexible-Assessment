from django.urls import path
from . import views

app_name = "accommodations"
urlpatterns = [
    path(
        "<int:course_id>/",
        views.AccommodationsHome.as_view(),
        name="accommodations_home",
    ),
    path(
        "<int:course_id>/quizzes",
        views.AccommodationsQuizzes.as_view(),
        name="accommodations_quizzes",
    ),
    path("<int:course_id>/upload_pdfs", views.upload_pdfs, name="upload_pdfs"),
]
