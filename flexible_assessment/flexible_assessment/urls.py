from django.contrib import admin
from django.urls import include, path

from . import views

urlpatterns = [
    path("student/", include("student.urls")),
    path("instructor/", include("instructor.urls")),
    path("admin/", admin.site.urls),
    path("launch/", views.launch, name="launch"),
    path("jwks/", views.get_jwks, name="jwks"),
    path("login/", views.login, name="login"),
    path("oauth/", include("oauth.urls")),
]
