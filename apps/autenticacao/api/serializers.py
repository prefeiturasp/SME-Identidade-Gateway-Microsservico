"""Serializers do fluxo de login e níveis de acesso.

Contratos de entrada/saída espelham o comportamento observado no
Swagger da API/EOL legada (``tasks/swaggere_eol.json``, tags
``Autenticacao`` e ``AutenticacaoSGP``), servindo como base estável
para o roteamento ao SME-Identidade-Token-Microsservico enquanto
este último está em desenvolvimento.
"""

from rest_framework import serializers

_AJUDA_LOGIN = "RF, CPF ou login do usuário."


class LoginRequestSerializer(serializers.Serializer):
    """Credenciais recebidas para autenticação de um usuário.

    Equivale ao ``AutenticacaoDto`` do legado
    (``POST /api/v1/autenticacao``).
    """

    login = serializers.CharField(help_text=_AJUDA_LOGIN)
    senha = serializers.CharField(
        write_only=True, help_text="Senha em texto plano (transporte HTTPS)."
    )


class LoginResponseSerializer(serializers.Serializer):
    """Resultado da autenticação de um usuário no Keycloak.

    Equivale ao retorno da Etapa 1 do fluxo legado
    (``usuarioId``, ``status``, ``nome``, ``codigoRf``), mas
    autenticado de verdade contra o Keycloak (grant type
    ``password``, via ``KeycloakOpenID``).
    """

    kc_user_id = serializers.CharField()
    username = serializers.CharField()
    nome = serializers.CharField()
    email = serializers.CharField(allow_null=True, required=False)
    ativo = serializers.BooleanField()
    cpf = serializers.CharField(allow_null=True, required=False)
    rf = serializers.CharField(allow_null=True, required=False)
    roles = serializers.DictField(
        help_text=(
            "realm_access/resource_access extraídos do access token,"
            " conforme os protocol mappers configurados no client"
            " Keycloak (formato bruto do Keycloak, sem filtragem)."
        )
    )
    access_token = serializers.CharField()
    refresh_token = serializers.CharField()
    expires_in = serializers.IntegerField(allow_null=True, required=False)


class PerfilSerializer(serializers.Serializer):
    """Perfil de acesso vinculado a um usuário em um sistema."""

    id = serializers.UUIDField()
    nome = serializers.CharField()
    ativo = serializers.BooleanField()


class PerfisPorLoginResponseSerializer(serializers.Serializer):
    """Perfis consolidados de um usuário.

    Equivale ao ``RetornoPerfisPorLoginDto``
    (``GET /api/AutenticacaoSgp/CarregarPerfisPorLogin/{login}``).
    """

    rf = serializers.CharField(allow_null=True, required=False)
    perfis = PerfilSerializer(many=True)


class PermissaoSerializer(serializers.Serializer):
    """Permissão individual concedida por um perfil de acesso."""

    codigo = serializers.IntegerField()
    descricao = serializers.CharField(allow_null=True, required=False)


class DadosAcessoResponseSerializer(serializers.Serializer):
    """Contexto de acesso completo de um usuário em um perfil.

    Equivale ao ``RetornoDadosAcessoUsuarioSgpDTO``
    (``GET /api/AutenticacaoSgp/CarregarDadosAcesso/usuarios/
    {login}/perfis/{perfil}``). O ``token`` aqui é o JWT
    enriquecido — composto pelo auth-gateway-ms a partir dos
    dados retornados pelo token-ms, não emitido por este serviço.
    """

    token = serializers.CharField()
    data_expiracao_token = serializers.DateTimeField()
    permissoes = PermissaoSerializer(many=True)


class DadosUsuarioResponseSerializer(serializers.Serializer):
    """Dados cadastrais de um usuário, consultados direto no Keycloak.

    Equivale ao ``DadosUsuarioDTO``
    (``GET /api/AutenticacaoSgp/{login}/dados``).
    """

    kc_user_id = serializers.CharField()
    username = serializers.CharField()
    nome = serializers.CharField()
    email = serializers.CharField(allow_null=True, required=False)
    ativo = serializers.BooleanField()
    cpf = serializers.CharField(allow_null=True, required=False)
    rf = serializers.CharField(allow_null=True, required=False)


class RecuperarSenhaRequestSerializer(serializers.Serializer):
    """Solicitação de recuperação de senha.

    Equivale a
    ``POST /api/v1/autenticacao/RecuperarSenha/usuario``. Delega
    integralmente ao Keycloak: nenhum token de recuperação é gerado
    por este serviço, o Keycloak envia o e-mail com o link.
    """

    login = serializers.CharField(help_text=_AJUDA_LOGIN)


class AlterarSenhaRequestSerializer(serializers.Serializer):
    """Solicitação de redefinição administrativa de senha.

    Equivale a ``POST /api/AutenticacaoSgp/AlterarSenha``. Define
    uma senha definitiva no Keycloak — não exige troca no próximo
    login.
    """

    login = serializers.CharField(help_text=_AJUDA_LOGIN)
    senha = serializers.CharField(
        write_only=True,
        help_text="Nova senha (transporte HTTPS).",
    )


class AlterarEmailRequestSerializer(serializers.Serializer):
    """Solicitação de alteração de e-mail.

    Equivale a ``POST /api/AutenticacaoSgp/AlterarEmail``. Atualiza
    o e-mail no Keycloak e reabre a verificação — o e-mail anterior
    deixa de ser considerado verificado até o usuário confirmar o
    novo endereço.
    """

    login = serializers.CharField(help_text=_AJUDA_LOGIN)
    email = serializers.EmailField(help_text="Novo endereço de e-mail.")


class OperacaoConfirmadaResponseSerializer(serializers.Serializer):
    """Confirmação genérica de que uma operação foi disparada.

    Usada nas rotas de gestão de credencial, cujo efeito real
    (envio de e-mail, troca de senha) ocorre de forma assíncrona no
    Keycloak — a resposta apenas confirma que a solicitação foi
    aceita e encaminhada.
    """

    situacao = serializers.CharField(default="solicitacao_enviada")


class AlterarEmailResponseSerializer(serializers.Serializer):
    """Confirmação da alteração de e-mail, com resultado da verificação.

    ``update_user`` (troca do e-mail) e ``send_verify_email`` (envio
    da notificação) não são atômicos no Keycloak — se a notificação
    falhar depois do e-mail já ter sido trocado, o cliente precisa
    saber disso em vez de receber um erro genérico que sugere que
    nada foi aplicado.
    """

    situacao = serializers.CharField(default="email_alterado")
    verificacao_enviada = serializers.BooleanField(
        help_text=(
            "False se o e-mail foi alterado mas o envio da"
            " notificação de verificação falhou — a troca já foi"
            " aplicada mesmo assim; repita a operação com o mesmo"
            " e-mail para reenviar a verificação."
        )
    )
