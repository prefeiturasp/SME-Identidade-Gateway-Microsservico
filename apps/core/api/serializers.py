"""Serializers base para todos os apps do core."""

from rest_framework import serializers


class HealthStatusSerializer(serializers.Serializer):
    """Serializa o resultado da verificação de saúde da aplicação.

    Este serializer é utilizado pelo endpoint de health check para
    informar o estado atual da aplicação e de suas dependências.

    Attributes:
        status: Estado geral da aplicação. Pode assumir os valores
            ``healthy``, ``degraded`` ou ``unhealthy``.
        dependencias: Estado das dependências externas (ex.:
            ``token_ms``) — nunca afeta ``status``, que reflete
            apenas a saúde do próprio serviço.
    """

    status = serializers.ChoiceField(
        choices=["healthy", "degraded", "unhealthy"],
        help_text="Estado geral do servico.",
    )
    dependencias = serializers.DictField(
        required=False,
        help_text=(
            "Estado das dependências externas (ex.: token_ms), sem"
            " afetar o status geral do próprio serviço."
        ),
    )
