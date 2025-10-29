from rest_framework import serializers
from .models import User
from core.auth import hash_password

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_repeat = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            "first_name", "last_name", "middle_name",
            "email", "password", "password_repeat"
        ]

    def validate(self, data):
        password = data.get("password")
        password_repeat = data.get("password_repeat")
        if password != password_repeat:
            raise serializers.ValidationError("Passwords do not match.")
        return data

    def create(self, validated_data):
        password = validated_data.pop("password")
        validated_data.pop("password_repeat", None)
        email = validated_data.get("email")
        if email:
            validated_data["email"] = email.strip().lower()
        validated_data["password_hash"] = hash_password(password)
        return User.objects.create(**validated_data)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id", "first_name", "last_name",
            "middle_name", "email", "is_active", "created_at"
        ]
        read_only_fields = ["id", "is_active", "created_at"]
