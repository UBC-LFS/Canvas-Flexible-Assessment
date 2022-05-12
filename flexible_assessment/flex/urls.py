from django.urls import path

from . import views

app_name = 'flex'
urlpatterns = [
    path('', views.index, name='index'),
    path('launch/', views.launch, name='launch'),
    path('jwks/', views.get_jwks, name='jwks'),
    path('login/', views.login, name='login'),
    path('instructor/', views.instuctor, name='instructor_view'),
    path('student/', views.student, name='student_view')
]
