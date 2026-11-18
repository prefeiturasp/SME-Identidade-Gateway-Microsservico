"""Contratos de entrada e saída da autenticação legada do SGP."""

from rest_framework import serializers


class DadosUsuarioSerializer(serializers.Serializer):
    """Serializa os dados cadastrais de um usuário."""

    cpf = serializers.CharField(
        allow_null=True,
        allow_blank=True,
        trim_whitespace=False,
        read_only=True,
    )
    nome = serializers.CharField(
        allow_null=True,
        allow_blank=True,
        trim_whitespace=False,
        read_only=True,
    )
    codigoRf = serializers.CharField(
        allow_null=True,
        read_only=True,
    )
    email = serializers.CharField(
        allow_null=True,
        allow_blank=True,
        trim_whitespace=False,
        read_only=True,
    )
    dreCodigo = serializers.CharField(
        allow_null=True,
        read_only=True,
    )
    emailValido = serializers.BooleanField(
        read_only=True,
    )
