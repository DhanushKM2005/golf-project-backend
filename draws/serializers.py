from rest_framework import serializers
from .models import Draw, DrawEntry, WinnerVerification


class DrawSerializer(serializers.ModelSerializer):
    entries_count = serializers.SerializerMethodField()
    winners_count = serializers.SerializerMethodField()

    class Meta:
        model = Draw
        fields = [
            'id', 'month', 'year', 'draw_type', 'status',
            'winning_numbers', 'jackpot_rollover_in', 'jackpot_rollover_out',
            'pool_breakdown', 'total_pool',
            'simulated_numbers', 'simulated_pool', 'simulated_breakdown',
            'simulated_rollover_out', 'simulated_winners',
            'entries_count', 'winners_count', 'created_at',
        ]
        read_only_fields = [
            'status', 'winning_numbers', 'jackpot_rollover_out',
            'pool_breakdown', 'total_pool',
            'simulated_numbers', 'simulated_pool', 'simulated_breakdown',
            'simulated_rollover_out', 'simulated_winners',
            'entries_count', 'winners_count', 'created_at',
        ]

    def get_entries_count(self, obj):
        return obj.entries.count()

    def get_winners_count(self, obj):
        return obj.winners.count()


class DrawEntrySerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    draw_label = serializers.SerializerMethodField()
    winning_numbers = serializers.JSONField(source='draw.winning_numbers', read_only=True)

    class Meta:
        model = DrawEntry
        fields = ['id', 'draw', 'draw_label', 'username', 'numbers', 'match_count', 'winning_numbers']

    def get_draw_label(self, obj):
        return f'{obj.draw.month:02d}/{obj.draw.year}'


class WinnerVerificationSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    draw_label = serializers.SerializerMethodField()
    proof_display = serializers.SerializerMethodField()

    class Meta:
        model = WinnerVerification
        fields = [
            'id', 'draw', 'draw_label', 'username', 'user_email',
            'match_count', 'prize_amount', 'proof_image', 'proof_image_url',
            'proof_display', 'review_status', 'payment_status', 'admin_notes',
            'reviewed_at', 'created_at',
        ]
        read_only_fields = ['id', 'draw_label', 'username', 'user_email', 'match_count', 'prize_amount', 'created_at']

    def get_draw_label(self, obj):
        return f'{obj.draw.month:02d}/{obj.draw.year}'

    def get_proof_display(self, obj):
        if obj.proof_image:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.proof_image.url) if request else obj.proof_image.url
        return obj.proof_image_url
