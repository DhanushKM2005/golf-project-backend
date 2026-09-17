from rest_framework import viewsets, permissions, filters
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from subscriptions.permissions import IsActiveSubscriber
from .models import Score
from .serializers import ScoreSerializer


class ScoreViewSet(viewsets.ModelViewSet):
    """
    PRD §05 Score Management System:
    Full CRUD on caller's own scores.
    Enforces active subscription via IsActiveSubscriber.
    Displays in reverse chronological order (Meta.ordering = ['-played_on']).
    """
    serializer_class = ScoreSerializer
    permission_classes = [IsAuthenticated, IsActiveSubscriber]

    def get_queryset(self):
        return Score.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class AdminScoreViewSet(viewsets.ModelViewSet):
    """
    PRD §11.01 Admin Score Management:
    Admins can view, search, filter, edit, or delete golf scores for any subscriber.
    """
    queryset = Score.objects.all().select_related('user').order_by('-played_on')
    serializer_class = ScoreSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [filters.SearchFilter]
    search_fields = ['user__username', 'user__email']

    def get_queryset(self):
        qs = super().get_queryset()
        user_id = self.request.query_params.get('user_id')
        if user_id:
            qs = qs.filter(user_id=user_id)
        return qs
