from rest_framework import serializers


class LoginRequestSerializer(serializers.Serializer):
    login = serializers.CharField(max_length=255)
    senha = serializers.CharField(max_length=255, trim_whitespace=False)


class TokenDataRequestSerializer(serializers.Serializer):
    usuarioId = serializers.UUIDField(required=False, allow_null=True)
    perfilId = serializers.UUIDField(required=False, allow_null=True)
    login = serializers.CharField(max_length=255, required=False, allow_blank=True)
