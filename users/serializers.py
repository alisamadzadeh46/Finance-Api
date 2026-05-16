from django.utils import timezone
from rest_framework import serializers
from .models import User, KYC


# ── Auth ──────────────────────────────────────────────────────────────────────

class UserRegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "password")
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        email = validated_data['email']
        local_part = email.split("@")[0]
        return User.objects.create_user(
            username=local_part,
            email=email,
            password=validated_data['password']
        )


# ── Profile ───────────────────────────────────────────────────────────────────

class UserSerializer(serializers.ModelSerializer):
    has_pin = serializers.SerializerMethodField()
    kyc_status = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "email", "username", "has_pin", "kyc_status"]

    def get_has_pin(self, obj):
        return bool(obj.transaction_pin)

    def get_kyc_status(self, obj):
        try:
            return obj.kyc_profile.verification_status
        except KYC.DoesNotExist:
            return "NOT_SUBMITTED"


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["username"]

    def validate_username(self, value):
        user = self.context['request'].user
        if User.objects.exclude(pk=user.pk).filter(username=value).exists():
            raise serializers.ValidationError("This username is already taken.")
        return value


# ── KYC ───────────────────────────────────────────────────────────────────────

class KYCSerializer(serializers.ModelSerializer):
    class Meta:
        model = KYC
        fields = ["id", "full_name", "date_of_birth", "id_type",
                  "id_image", "verification_status", "rejection_reason",
                  "created_at", "updated_at"]
        read_only_fields = ["verification_status", "rejection_reason", "created_at", "updated_at"]


class KYCCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = KYC
        fields = ["full_name", "date_of_birth", "id_type", "id_image"]

    def validate_date_of_birth(self, value):
        if value >= timezone.now().date():
            raise serializers.ValidationError("Date of birth must be in the past.")
        return value

    def validate_full_name(self, value):
        if len(value.strip()) < 3:
            raise serializers.ValidationError("Full name is too short.")
        return value

    def create(self, validated_data):
        user = self.context["request"].user
        if hasattr(user, "kyc_profile"):
            raise serializers.ValidationError(
                "You already submitted KYC. Contact support for changes."
            )
        return KYC.objects.create(user=user, **validated_data)


class KYCAdminUpdateSerializer(serializers.ModelSerializer):
    """For admin: approve or reject a KYC submission."""
    class Meta:
        model = KYC
        fields = ["verification_status", "rejection_reason"]

    def validate(self, attrs):
        status = attrs.get("verification_status")
        reason = attrs.get("rejection_reason", "")
        if status == KYC.VerificationStatus.REJECTED and not reason:
            raise serializers.ValidationError(
                {"rejection_reason": "A rejection reason is required when rejecting KYC."}
            )
        return attrs


# ── Transaction PIN ───────────────────────────────────────────────────────────

class SetPINSerializer(serializers.Serializer):
    pin = serializers.CharField(min_length=4, max_length=8, write_only=True)
    confirm_pin = serializers.CharField(min_length=4, max_length=8, write_only=True)

    def validate_pin(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("PIN must contain digits only.")
        return value

    def validate(self, attrs):
        if attrs['pin'] != attrs['confirm_pin']:
            raise serializers.ValidationError({"confirm_pin": "PINs do not match."})
        return attrs


class ChangePINSerializer(serializers.Serializer):
    current_pin = serializers.CharField(write_only=True)
    new_pin = serializers.CharField(min_length=4, max_length=8, write_only=True)
    confirm_new_pin = serializers.CharField(min_length=4, max_length=8, write_only=True)

    def validate_new_pin(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("PIN must contain digits only.")
        return value

    def validate(self, attrs):
        if attrs['new_pin'] != attrs['confirm_new_pin']:
            raise serializers.ValidationError({"confirm_new_pin": "New PINs do not match."})
        return attrs


class VerifyPINSerializer(serializers.Serializer):
    pin = serializers.CharField(write_only=True)
