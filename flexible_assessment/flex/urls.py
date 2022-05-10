from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('launch/', views.launch, name='launch'),
    path('jwks/', views.get_jwks, name='jwks'),
    path('login/', views.login, name='login')
]