from django.urls import path

from . import views

app_name = 'flex'
urlpatterns = [
    path('', views.index, name='index'),
    path('launch/', views.launch, name='launch'),
    path('jwks/', views.get_jwks, name='jwks'),
    path('login/', views.login, name='login'),
    path('instructor/', views.instructor_home, name='instructor_home'),
    path(
        'instructor/assessment/',
        views.InstructorListView.as_view(),
        name='instructor_list'),
    path(
        'instructor/asssessment/<slug:pk>/',
        views.InstructorAssessmentDetailView.as_view(),
        name='inst_assessment_detail'),
    path(
        'instructor/assessment/add',
        views.AssessmentCreate.as_view(),
        name='add_assessment'),
    path(
        'instructor/assessment/<slug:pk>/update/',
        views.AssessmentUpdate.as_view(),
        name='update_assessment'),
    path(
        'instructor/assessment/<slug:pk>/delete/',
        views.AssessmentDelete.as_view(),
        name='delete_assessment'),
    path(
        'instructor/course/<slug:pk>/date/update',
        views.DateUpdate.as_view(),
        name='update_date'),
    path('student/', views.student_home, name='student_home'),
    path(
        'student/assessment/',
        views.StudentListView.as_view(),
        name='student_list'),
    path(
        'student/flex/<slug:pk>/update',
        views.FlexAssessmentUpdate.as_view(),
        name='update_flex')
]
