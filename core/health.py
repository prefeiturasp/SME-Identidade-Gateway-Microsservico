"""Health-check views for gateway-ms."""
from django.http import JsonResponse


def liveness(_request):
    return JsonResponse({"status": "ok", "service": "gateway-ms"})


def readiness(_request):
    # In production add real probes for Keycloak / token-ms / cache.
    return JsonResponse({"status": "ready", "service": "gateway-ms"})
