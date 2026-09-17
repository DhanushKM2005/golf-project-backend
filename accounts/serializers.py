from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.utils import timezone
from datetime import timedelta
from rest_framework import serializers
from subscriptions.models import Subscription
from charities.models import Charity
from django.conf import settings

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    charity_id = serializers.PrimaryKeyRelatedField(
        queryset=Charity.objects.all(), required=False, allow_null=True, write_only=True
    )
    charity_percentage = serializers.IntegerField(
        required=False, default=10, min_value=10, max_value=100, write_only=True
    )
    plan = serializers.ChoiceField(
        choices=['monthly', 'yearly'], default='monthly', write_only=True
    )

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'phone', 'charity_id', 'charity_percentage', 'plan']

    def create(self, validated_data):
        charity = validated_data.pop('charity_id', None)
        charity_percentage = validated_data.pop('charity_percentage', settings.MIN_CHARITY_PERCENT)
        plan = validated_data.pop('plan', 'monthly')

        user = User.objects.create_user(**validated_data)

        # PRD §08.1: Users select a charity and plan at signup
        days = 365 if plan == 'yearly' else 30
        Subscription.objects.create(
            user=user,
            plan=plan,
            status='active',
            charity=charity,
            charity_percentage=max(charity_percentage, settings.MIN_CHARITY_PERCENT),
            renews_at=timezone.now() + timedelta(days=days),
        )
        return user


class UserSerializer(serializers.ModelSerializer):
    role = serializers.ReadOnlyField()
    subscription_status = serializers.SerializerMethodField()
    subscription_plan = serializers.SerializerMethodField()
    subscription_renews_at = serializers.SerializerMethodField()
    charity_id = serializers.SerializerMethodField()
    charity_name = serializers.SerializerMethodField()
    charity_percentage = serializers.SerializerMethodField()
    scores_count = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'phone', 'role', 'is_active', 'is_staff', 'date_joined',
            'subscription_status', 'subscription_plan', 'subscription_renews_at',
            'charity_id', 'charity_name', 'charity_percentage', 'scores_count',
        ]
        read_only_fields = ['id', 'role', 'is_staff', 'date_joined']

    def get_subscription_status(self, obj):
        sub = getattr(obj, 'subscription', None)
        if sub:
            sub.check_lapsed()
            return sub.status
        return 'inactive'

    def get_subscription_plan(self, obj):
        sub = getattr(obj, 'subscription', None)
        return sub.plan if sub else None

    def get_subscription_renews_at(self, obj):
        sub = getattr(obj, 'subscription', None)
        return sub.renews_at if sub else None

    def get_charity_id(self, obj):
        sub = getattr(obj, 'subscription', None)
        return sub.charity_id if sub else None

    def get_charity_name(self, obj):
        sub = getattr(obj, 'subscription', None)
        return sub.charity.name if sub and sub.charity else None

    def get_charity_percentage(self, obj):
        sub = getattr(obj, 'subscription', None)
        return sub.charity_percentage if sub else None

    def get_scores_count(self, obj):
        return obj.scores.count()
