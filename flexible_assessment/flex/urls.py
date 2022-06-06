from django.urls import path

from . import views, insturctor_views, student_views

app_name = 'flex'
urlpatterns = [
    path('', views.index, name='index'),
    path('launch/', views.launch, name='launch'),
    path('jwks/', views.get_jwks, name='jwks'),
    path('login/', views.login, name='login'),
    path('instructor/', views.instructor_home, name='instructor_home'),
    path(
        'instructor/form/',
        insturctor_views.InstructorFormView.as_view(),
        name='instructor_form'),
    path(
        'instructor/percentages/',
        insturctor_views.FlexAssessmentListView.as_view(),
        name='percentage_list'),
    path(
        'instructor/percentages/csv/',
        insturctor_views.FlexAssessmentListView.as_view(),
        {'csv': True},
        name='percentage_list_export'),
    path(
        'instructor/percentages/<slug:pk>/',
        insturctor_views.OverrideStudentFormView.as_view(),
        name='override_student_form'),
    path(
        'instructor/final/match/',
        insturctor_views.AssessmentGroupView.as_view(),
        name='group_form'),
    path(
        'instructor/final/list/',
        insturctor_views.FinalGradeListView.as_view(),
        name='final_grades'),
    path(
        'instructor/final/list/csv/',
        insturctor_views.FinalGradeListView.as_view(),
        {'csv': True},
        name='final_grades_export'),
    path('student/', views.student_home, name='student_home'),
    path(
        'student/form/',
        student_views.StudentFormView.as_view(),
        name='student_form')
]
