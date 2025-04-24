from django.contrib import admin
from django.urls import include, path

from . import views
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("student/", include("student.urls")),
    path("instructor/", include("instructor.urls")),
    path("admin/", admin.site.urls),
    path("launch/", views.launch, name="launch"),
    path("jwks/", views.get_jwks, name="jwks"),
    path("login/", views.login, name="login"),
    path("oauth/", include("oauth.urls")),
    path("due_dates/", include("due_dates.urls"))
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
