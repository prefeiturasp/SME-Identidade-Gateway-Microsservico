from django.urls import path

from . import views

urlpatterns = [
    path("token/", views.token, name="oidc-token"),
    path("refresh/", views.refresh, name="oidc-refresh"),
    path("introspect/", views.introspect, name="oidc-introspect"),
    path("logout/", views.logout, name="oidc-logout"),
    path(".well-known/openid-configuration", views.well_known, name="oidc-discovery"),
    path("certs/", views.jwks, name="oidc-jwks"),
]
