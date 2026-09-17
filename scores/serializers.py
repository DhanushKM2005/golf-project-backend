from rest_framework import serializers
from .models import Score


class ScoreSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = Score
        fields = ['id', 'username', 'value', 'played_on', 'created_at']
        read_only_fields = ['id', 'username', 'created_at']

    def validate_value(self, value):
        if value < 1 or value > 45:
            raise serializers.ValidationError(
                'Score must be between 1 and 45 (Stableford format).'
            )
        return value

    def validate(self, attrs):
        user = self.instance.user if self.instance else self.context['request'].user
        played_on = attrs.get(
            'played_on',
            self.instance.played_on if self.instance else None
        )

        if played_on:
            qs = Score.objects.filter(user=user, played_on=played_on)

            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                raise serializers.ValidationError(
                    'A score already exists for that date — edit it instead of adding a new one.'
                )

        return attrs

    def create(self, validated_data):
        user = validated_data.pop(
            'user',
            self.context['request'].user
        )

        score = Score.objects.create(
            user=user,
            **validated_data
        )

        # Keep only the 5 most recent scores
        stale = Score.objects.filter(
            user=user
        ).order_by('-played_on')[5:]

        if stale.exists():
            Score.objects.filter(
                pk__in=[s.pk for s in stale]
            ).delete()

        return score