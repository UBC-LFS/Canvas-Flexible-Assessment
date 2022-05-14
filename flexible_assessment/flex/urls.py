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
        'instructor/list/',
        views.InstructorListView.as_view(),
        name='instructor_list'),
    path('instructor/asssessment/<slug:pk>/', views.InstructorAssessmentDetailView.as_view(), name='inst_assessment_detail'),
    path('instructor/add/', views.add_assessment, name='add_assessment'),
    path('student/', views.student, name='student_view')
]
