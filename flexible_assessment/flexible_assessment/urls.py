from django.contrib import admin
from django.urls import include, path

from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("flexible_assessment/student/", include("student.urls")),
    path("flexible_assessment/instructor/", include("instructor.urls")),
    path("accommodations/", include("accommodations.urls")),
    path("admin/", admin.site.urls),
    path(
        "launch/flexible_assessment/",
        views.launch_flexible_assessment,
        name="launch_flexible_assessment",
    ),
    path(
        "launch/accommodations/",
        views.launch_accommodations,
        name="launch_accommodations",
    ),
    path("jwks/", views.get_jwks, name="jwks"),
    path("login/", views.login, name="login"),
    path("oauth/", include("oauth.urls")),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
