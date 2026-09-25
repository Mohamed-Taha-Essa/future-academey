from django.urls import path

from . import views

urlpatterns = [
    path("", views.home_view, name="home"),
    path("services/<slug:slug>/", views.service_detail_view, name="service_detail"),
    path("courses/<slug:slug>/", views.course_detail_view, name="course_detail"),
]
