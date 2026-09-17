from django.conf import settings
from rest_framework import serializers
from .models import Subscription


class SubscriptionSerializer(serializers.ModelSerializer):
    charity_name = serializers.CharField(source='charity.name', read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    fee = serializers.IntegerField(read_only=True)

    class Meta:
        model = Subscription
        fields = [
            'id', 'username', 'user_email', 'plan', 'status', 'charity', 'charity_name',
            'charity_percentage', 'fee', 'started_at', 'renews_at',
        ]
        read_only_fields = ['id', 'username', 'user_email', 'fee', 'started_at']

    def validate_charity_percentage(self, value):
        if value < settings.MIN_CHARITY_PERCENT:
            raise serializers.ValidationError(
                f'Charity contribution cannot be below {settings.MIN_CHARITY_PERCENT}%.'
            )
        return value
