from django.urls import path

from . import health

urlpatterns = [
    path("", health.liveness, name="health-liveness"),
    path("ready/", health.readiness, name="health-readiness"),
]
