from django.urls import path

from . import views

app_name = 'instructor'
urlpatterns = [
    path('instructor/', views.instructor_home, name='instructor_home'),
    path(
        'instructor/form/',
        views.InstructorFormView.as_view(),
        name='instructor_form'),
    path(
        'instructor/percentages/',
        views.FlexAssessmentListView.as_view(),
        name='percentage_list'),
    path(
        'instructor/percentages/csv/',
        views.FlexAssessmentListView.as_view(),
        {'csv': True},
        name='percentage_list_export'),
    path(
        'instructor/percentages/<slug:pk>/',
        views.OverrideStudentFormView.as_view(),
        name='override_student_form'),
    path(
        'instructor/final/match/',
        views.AssessmentGroupView.as_view(),
        name='group_form'),
    path(
        'instructor/final/list/',
        views.FinalGradeListView.as_view(),
        name='final_grades'),
    path(
        'instructor/final/list/csv/',
        views.FinalGradeListView.as_view(),
        {'csv': True},
        name='final_grades_export'),
]