from django.urls import path

from . import views

app_name = "certificate_app"

urlpatterns = [
    path("<slug:certificate_id>/", views.certificate_view, name="certificate"),
]
