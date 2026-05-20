from django.urls import path

from . import views

urlpatterns = [
    path("token/", views.issue_token, name="m2m-token"),
    path("introspect/", views.introspect, name="m2m-introspect"),
]
