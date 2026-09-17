from rest_framework import serializers
from .models import Charity, CharityEvent, Donation


class CharityEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = CharityEvent
        fields = ['id', 'charity', 'title', 'description', 'location', 'event_date', 'created_at']
        read_only_fields = ['id', 'created_at']


class CharitySerializer(serializers.ModelSerializer):
    events = CharityEventSerializer(many=True, read_only=True)
    subscribers_count = serializers.SerializerMethodField()
    image_display = serializers.SerializerMethodField()

    class Meta:
        model = Charity
        fields = [
            'id', 'name', 'category', 'tagline', 'description',
            'image_url', 'image', 'image_display', 'website_url',
            'is_featured', 'is_active', 'events', 'subscribers_count',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'subscribers_count']

    def get_subscribers_count(self, obj):
        return obj.subscribers.filter(status='active').count()

    def get_image_display(self, obj):
        if obj.image:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.image.url) if request else obj.image.url
        return obj.image_url


class DonationSerializer(serializers.ModelSerializer):
    charity_name = serializers.CharField(source='charity.name', read_only=True)

    class Meta:
        model = Donation
        fields = [
            'id', 'charity', 'charity_name', 'donor_user',
            'donor_name', 'donor_email', 'amount', 'message', 'created_at',
        ]
        read_only_fields = ['id', 'created_at']

    def validate_amount(self, value):
        if value < 50:
            raise serializers.ValidationError('Minimum donation amount is ₹50.')
        return value
