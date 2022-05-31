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
        'instructor/course/<slug:pk>/date/update',
        insturctor_views.DateUpdate.as_view(),
        name='update_date'),
    path(
        'instructor/percentages/',
        insturctor_views.FlexAssessmentListView.as_view(),
        name='percentage_list'),
    path(
        'instructor/final/1/',
        insturctor_views.AssessmentGroupView.as_view(),
        name='group_form'),
    path(
        'instructor/final/2/',
        insturctor_views.FinalGradeListView.as_view(),
        name='final_grades'),
    path('student/', views.student_home, name='student_home'),
    path(
        'student/form/',
        student_views.StudentFormView.as_view(),
        name='student_form')
]
