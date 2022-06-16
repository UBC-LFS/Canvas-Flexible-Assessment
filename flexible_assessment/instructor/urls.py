from django.urls import path

from . import views


app_name = 'instructor'
urlpatterns = [
    path('', views.instructor_home, name='instructor_home'),
    path(
        'form/',
        views.InstructorFormView.as_view(),
        name='instructor_form'),
    path(
        'percentages/',
        views.FlexAssessmentListView.as_view(),
        name='percentage_list'),
    path(
        'percentages/csv/',
        views.FlexAssessmentListView.as_view(),
        {'csv': True},
        name='percentage_list_export'),
    path(
        'percentages/<slug:pk>/',
        views.OverrideStudentFormView.as_view(),
        name='override_student_form'),
    path(
        'final/match/',
        views.AssessmentGroupView.as_view(),
        name='group_form'),
    path(
        'final/list/',
        views.FinalGradeListView.as_view(),
        name='final_grades'),
    path(
        'final/list/csv/',
        views.FinalGradeListView.as_view(),
        {'csv': True},
        name='final_grades_export'),
    path(
        'final/list/submit/',
        views.FinalGradeListView.as_view(),
        {'submit': True},
        name='final_grades_submit'),
]
