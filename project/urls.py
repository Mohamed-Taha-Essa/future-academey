from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

from certificate_app.views import set_language_view

urlpatterns = [
    path("", include("academy_app.urls")),
    path("certificate/", include("certificate_app.urls")),
    # Django's i18n URLs are required for Unfold's language switcher.
    # NOTE: django.conf.urls.i18n also registers a view named "set_language"
    # at /i18n/setlang/. Registering the project's custom endpoint AFTER the
    # include keeps {% url 'set_language' %} resolving to the certificate
    # app's session+cookie view used by the public header switcher.
    path("i18n/", include("django.conf.urls.i18n")),
    path("set-language/", set_language_view, name="set_language"),
    path("admin/", admin.site.urls),
]

# Serve media files in development (only when local storage defines them;
# R2/S3 mode serves media from the remote bucket and sets no MEDIA_URL).
if settings.DEBUG and getattr(settings, "MEDIA_URL", None):
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
