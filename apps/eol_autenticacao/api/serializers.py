"""Contratos de entrada e saída da autenticação legada."""

from rest_framework import serializers


class AutenticacaoExternaRequestSerializer(serializers.Serializer):
    """Recebe as credenciais e o sistema da autenticação externa."""

    usuario = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        default=None,
        trim_whitespace=False,
    )
    senha = serializers.CharField(
        required=False,
        allow_null=True,
        allow_blank=True,
        default=None,
        trim_whitespace=False,
        write_only=True,
    )
    codigoSistema = serializers.IntegerField(
        required=False,
        default=0,
        min_value=-(2**63),
        max_value=2**63 - 1,
    )


class CargoExternoSerializer(serializers.Serializer):
    """Representa um cargo ou uma função sobreposta."""

    codigo = serializers.IntegerField()
    nome = serializers.CharField(trim_whitespace=False)


class UnidadeExternaSerializer(serializers.Serializer):
    """Representa uma unidade de lotação ou exercício."""

    codigo = serializers.CharField(trim_whitespace=False)
    nomeUnidade = serializers.CharField(trim_whitespace=False)


class DadosFuncionaisExternosSerializer(serializers.Serializer):
    """Valida o contrato funcional do MS-Abrangência."""

    cargos = CargoExternoSerializer(many=True, allow_null=True)
    cargosSobrePosto = CargoExternoSerializer(
        many=True,
        allow_null=True,
    )
    unidadesLotacao = UnidadeExternaSerializer(
        many=True,
        allow_null=True,
    )
    unidadeExercicio = UnidadeExternaSerializer(allow_null=True)


class RetornoUsuarioExternoSerializer(serializers.Serializer):
    """Serializa os campos de RetornoUsuarioExternoDTO."""

    usuarioId = serializers.UUIDField(read_only=True)
    nome = serializers.CharField(allow_null=True, read_only=True)
    codigoRf = serializers.CharField(allow_null=True, read_only=True)
    numeroDocumento = serializers.CharField(
        allow_null=True,
        read_only=True,
    )
    email = serializers.CharField(allow_null=True, read_only=True)
    perfis = serializers.ListField(
        child=serializers.UUIDField(),
        read_only=True,
    )
    cargos = CargoExternoSerializer(
        many=True,
        allow_null=True,
        read_only=True,
    )
    cargosSobrePosto = CargoExternoSerializer(
        many=True,
        allow_null=True,
        read_only=True,
    )
    unidadesLotacao = UnidadeExternaSerializer(
        many=True,
        allow_null=True,
        read_only=True,
    )
    unidadeExercicio = UnidadeExternaSerializer(
        allow_null=True,
        read_only=True,
    )
