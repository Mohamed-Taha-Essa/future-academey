from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

from certificate_app.views import home_view, set_language_view

urlpatterns = [
    path("", home_view, name="home"),
    path("certificate/", include("certificate_app.urls")),
    path("set-language/", set_language_view, name="set_language"),
    path("i18n/", include("django.conf.urls.i18n")),  # Required for Unfold language switcher
    path("admin/", admin.site.urls),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
