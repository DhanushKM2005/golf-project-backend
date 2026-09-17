from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser

from .serializers import UserSerializer
from subscriptions.models import Subscription
from subscriptions.serializers import SubscriptionSerializer
from scores.models import Score
from scores.serializers import ScoreSerializer

User = get_user_model()


class UserAdminViewSet(viewsets.ModelViewSet):
    """
    PRD §11.01 User Management:
    - View and edit user profiles
    - Manage subscriptions (status, plan, dates)
    - View/manage golf scores for any user
    """
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
    permission_classes = [IsAdminUser]
    filter_backends = [filters.SearchFilter]
    search_fields = ['username', 'email', 'phone']

    def get_queryset(self):
        qs = super().get_queryset()
        role = self.request.query_params.get('role')
        if role == 'admin':
            qs = qs.filter(is_staff=True)
        elif role == 'subscriber':
            qs = qs.filter(is_staff=False)

        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            qs = qs.filter(is_active=(is_active.lower() == 'true'))
        return qs

    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        user = self.get_object()
        user.is_active = not user.is_active
        user.save()
        return Response({'id': user.id, 'username': user.username, 'is_active': user.is_active})

    @action(detail=True, methods=['get', 'post'])
    def subscription(self, request, pk=None):
        user = self.get_object()
        sub, _ = Subscription.objects.get_or_create(
            user=user,
            defaults={'plan': 'monthly', 'renews_at': timezone.now() + timedelta(days=30)}
        )
        if request.method == 'POST':
            serializer = SubscriptionSerializer(sub, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        return Response(SubscriptionSerializer(sub).data)

    @action(detail=True, methods=['get'])
    def scores(self, request, pk=None):
        user = self.get_object()
        user_scores = Score.objects.filter(user=user).order_by('-played_on')
        return Response(ScoreSerializer(user_scores, many=True).data)
