from django.urls import path

from . import views


app_name = 'instructor'
urlpatterns = [
    path(
        '<int:course_id>/',
        views.InstructorHome.as_view(),
        name='instructor_home'),
    path(
        '<int:course_id>/form/',
        views.InstructorAssessmentView.as_view(),
        name='instructor_form'),
    path(
        '<int:course_id>/form/csv',
        views.InstructorAssessmentView.as_view(),
        {'csv': True},
        name='assessments_export'),
    path(
        '<int:course_id>/form/upload',
        views.ImportAssessmentView.as_view(),
        name='file_upload'),
    path(
        '<int:course_id>/percentages/',
        views.FlexAssessmentListView.as_view(),
        name='percentage_list'),
    path(
        '<int:course_id>/percentages/csv/',
        views.FlexAssessmentListView.as_view(),
        {'csv': True},
        name='percentage_list_export'),
    path(
        '<int:course_id>/percentages/<slug:pk>/',
        views.OverrideStudentAssessmentView.as_view(),
        name='override_student_form_percentage'),
    path(
        '<int:course_id>/percentages/<slug:pk>/final',
        views.OverrideStudentAssessmentView.as_view(),
        name='override_student_form_final'),
    path(
        '<int:course_id>/final/match/',
        views.AssessmentGroupView.as_view(),
        name='group_form'),
    path(
        '<int:course_id>/final/list/',
        views.FinalGradeListView.as_view(),
        name='final_grades'),
    path(
        '<int:course_id>/final/list/csv/',
        views.FinalGradeListView.as_view(),
        {'csv': True},
        name='final_grades_export'),
    path(
        '<int:course_id>/final/list/submit/',
        views.FinalGradeListView.as_view(),
        {'submit': True},
        name='final_grades_submit')
]
