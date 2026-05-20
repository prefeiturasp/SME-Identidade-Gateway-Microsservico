from rest_framework import serializers


class TokenRequestSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=255)
    password = serializers.CharField(max_length=255, trim_whitespace=False)
    client_id = serializers.CharField(max_length=255, required=False, allow_blank=True)
    client_secret = serializers.CharField(
        max_length=512, required=False, allow_blank=True, trim_whitespace=False
    )
    scope = serializers.CharField(max_length=255, required=False, allow_blank=True)


class RefreshRequestSerializer(serializers.Serializer):
    refresh_token = serializers.CharField(max_length=8192, trim_whitespace=False)
    client_id = serializers.CharField(max_length=255, required=False, allow_blank=True)
    client_secret = serializers.CharField(
        max_length=512, required=False, allow_blank=True, trim_whitespace=False
    )


class IntrospectRequestSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=8192, trim_whitespace=False)


class LogoutRequestSerializer(serializers.Serializer):
    refresh_token = serializers.CharField(max_length=8192, trim_whitespace=False)
