"""Contratos de entrada e saída da autenticação legada do SGP."""

from rest_framework import serializers


class ValidarEmailExistenteRequestSerializer(serializers.Serializer):
    """Valida os parâmetros de caminho da consulta de e-mail."""

    login = serializers.CharField(
        help_text="RF ou CPF do usuário a excluir da busca."
    )
    email = serializers.EmailField(help_text="E-mail completo a consultar.")


class ErroConsultaUsuariosSerializer(serializers.Serializer):
    """Erro de identificação do usuário ou de consulta ao provedor."""

    erro = serializers.CharField()

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
