"""Serializers do domínio de gestão de usuário.

Os nomes de campo espelham exatamente os serializers equivalentes do
SME-Identidade-ETL (``apps/controle_etl/serializers.py``) — não é
uma tradução de contrato, é o mesmo contrato, para que a view do
Gateway apenas valide e repasse o payload sem transformação.
"""

from rest_framework import serializers

_AJUDA_IDENTIFICADOR = "RF, CPF ou email do usuário."
_AJUDA_REALM = "Realm Keycloak."


class CriarUsuarioSerializer(serializers.Serializer):
    """Payload de criação de usuário sem vínculo prévio no CoreSSO.

    Equivale a ``CriarUsuarioManualSerializer`` do ETL. ``sistema``/
    ``roles`` são opcionais: quando informados juntos, o ETL concede
    o acesso na mesma chamada de criação.
    """

    nome = serializers.CharField()
    cpf = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    rf = serializers.CharField(required=False, allow_blank=True)
    tipo_usuario = serializers.ChoiceField(
        choices=["servidor", "aluno", "terceiro"],
        default="terceiro",
    )
    sistema = serializers.IntegerField(
        required=False,
        help_text="coresso_sis_id do sistema alvo (opcional).",
    )
    roles = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        help_text="Nomes dos roles/perfis a conceder (opcional).",
    )
    realm = serializers.CharField(required=False, allow_blank=True)

    def validate(self, dados: dict) -> dict:
        """Exige identificador e, se houver roles, também o sistema.

        Args:
            dados: Campos já validados individualmente.

        Returns:
            Os mesmos dados, se a validação cruzada passar.

        Raises:
            ValidationError: Se nem CPF nem RF forem informados, ou
                se ``roles`` vier sem ``sistema`` (ou vice-versa).
        """
        if not dados.get("cpf") and not dados.get("rf"):
            raise serializers.ValidationError("Informe ao menos cpf ou rf.")
        tem_sistema = "sistema" in dados
        tem_roles = bool(dados.get("roles"))
        if tem_roles != tem_sistema:
            raise serializers.ValidationError(
                "Informe sistema e roles juntos, ou nenhum dos dois."
            )
        return dados


class SincronizarUsuarioSerializer(serializers.Serializer):
    """Payload de sincronização de usuário existente no CoreSSO."""

    identificador = serializers.CharField(help_text=_AJUDA_IDENTIFICADOR)
    realm = serializers.CharField(required=False, allow_blank=True)


class ConcederAcessoSerializer(serializers.Serializer):
    """Payload de concessão de acesso a um sistema e roles."""

    identificador = serializers.CharField(help_text=_AJUDA_IDENTIFICADOR)
    sistema = serializers.IntegerField(
        help_text="coresso_sis_id do sistema alvo."
    )
    roles = serializers.ListField(
        child=serializers.CharField(),
        min_length=1,
        help_text="Nomes dos roles/perfis a conceder.",
    )
    realm = serializers.CharField(required=False, allow_blank=True)


class RespostaGenericaSerializer(serializers.Serializer):
    """Resposta genérica de operações de gestão de usuário.

    Não é usada para gerar o payload de saída (a resposta do ETL é
    repassada como veio) — serve apenas para documentar o formato
    esperado no Swagger.
    """

    acao = serializers.CharField()
    kc_user_id = serializers.CharField(required=False)
