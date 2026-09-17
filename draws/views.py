from django.utils import timezone
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from .models import Draw, DrawEntry, WinnerVerification
from .serializers import DrawSerializer, DrawEntrySerializer, WinnerVerificationSerializer
from .engine import simulate_draw, publish_draw
from subscriptions.models import Subscription
from subscriptions.permissions import IsActiveSubscriber


class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_staff)


class DrawViewSet(viewsets.ModelViewSet):
    """
    PRD §11.02 Draw Management:
    - Admin controls configuring draw logic (random vs algorithmic)
    - Run simulations before publishing
    - Publish results with rollover calculations
    """
    queryset = Draw.objects.all()
    serializer_class = DrawSerializer
    permission_classes = [IsAdmin]

    @action(detail=True, methods=['post'])
    def simulate(self, request, pk=None):
        draw = self.get_object()
        if draw.status == 'published':
            return Response({'error': 'Published draw cannot be re-simulated.'}, status=status.HTTP_400_BAD_REQUEST)
        result = simulate_draw(draw)
        return Response(result)

    @action(detail=True, methods=['post'])
    def publish(self, request, pk=None):
        draw = self.get_object()
        if draw.status == 'published':
            return Response({'error': 'Draw is already published.'}, status=status.HTTP_400_BAD_REQUEST)
        winning_numbers = request.data.get('winning_numbers')
        publish_draw(draw, winning_numbers=winning_numbers)
        return Response(DrawSerializer(draw, context={'request': request}).data)


class PublicDrawViewSet(viewsets.ReadOnlyModelViewSet):
    """
    PRD §01 & §06 Public / Subscriber draw overview:
    Allows visitors and subscribers to view published draws, winning numbers,
    and upcoming prize pool estimates.
    """
    queryset = Draw.objects.filter(status='published').order_by('-year', '-month')
    serializer_class = DrawSerializer
    permission_classes = [permissions.AllowAny]

    @action(detail=False, methods=['get'])
    def latest(self, request):
        latest_draw = Draw.objects.filter(status='published').order_by('-year', '-month').first()
        active_count = Subscription.objects.filter(status='active').count()
        next_jackpot = latest_draw.jackpot_rollover_out if latest_draw else 0
        return Response({
            'latest_draw': DrawSerializer(latest_draw, context={'request': request}).data if latest_draw else None,
            'active_subscribers': active_count,
            'current_rollover_jackpot': next_jackpot,
        })

    @action(detail=False, methods=['get'])
    def upcoming(self, request):
        active_count = Subscription.objects.filter(status='active').count()
        latest_draw = Draw.objects.filter(status='published').order_by('-year', '-month').first()
        rollover = latest_draw.jackpot_rollover_out if latest_draw else 0
        est_pool = int(active_count * 999 * 0.15) + rollover
        return Response({
            'active_subscribers': active_count,
            'rollover_in': rollover,
            'estimated_total_pool': est_pool,
            'estimated_5_match_jackpot': int(est_pool * 0.40),
            'estimated_4_match_pool': int(est_pool * 0.35),
            'estimated_3_match_pool': int(est_pool * 0.25),
        })


class MyDrawEntriesView(viewsets.ReadOnlyModelViewSet):
    """
    PRD §10 Participation Summary:
    A subscriber's own draw entries and tickets.
    """
    serializer_class = DrawEntrySerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return DrawEntry.objects.filter(user=self.request.user).select_related('draw').order_by('-draw__year', '-draw__month')


class WinnerVerificationViewSet(viewsets.ModelViewSet):
    """
    PRD §09 Winner Verification & §11.04 Winners Management:
    - Winners upload golf score screenshot proof
    - Admin reviews submission (approve / reject)
    - Admin updates payment status (pending -> paid)
    """
    serializer_class = WinnerVerificationSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        if self.request.user.is_staff:
            qs = WinnerVerification.objects.all().select_related('user', 'draw')
            status_param = self.request.query_params.get('review_status')
            if status_param:
                qs = qs.filter(review_status=status_param)
            payout_param = self.request.query_params.get('payment_status')
            if payout_param:
                qs = qs.filter(payment_status=payout_param)
            return qs
        return WinnerVerification.objects.filter(user=self.request.user).select_related('draw')

    def get_permissions(self):
        if self.action in ('update', 'partial_update', 'destroy', 'approve', 'reject', 'mark_paid'):
            return [IsAdmin()]
        return [permissions.IsAuthenticated()]

    @action(detail=True, methods=['post'])
    def upload_proof(self, request, pk=None):
        """Winner submits score screenshot proof"""
        winning = self.get_object()
        if not request.user.is_staff and winning.user != request.user:
            return Response({'error': 'Permission denied.'}, status=status.HTTP_403_FORBIDDEN)

        proof_file = request.FILES.get('proof_image')
        proof_url = request.data.get('proof_image_url')

        if not proof_file and not proof_url:
            return Response({'error': 'Please provide an image file or URL.'}, status=status.HTTP_400_BAD_REQUEST)

        if proof_file:
            winning.proof_image = proof_file
        if proof_url:
            winning.proof_image_url = proof_url

        winning.review_status = 'pending'
        winning.save()
        return Response(WinnerVerificationSerializer(winning, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        winning = self.get_object()
        winning.review_status = 'approved'
        winning.reviewed_at = timezone.now()
        winning.admin_notes = request.data.get('admin_notes', winning.admin_notes)
        winning.save()
        return Response(WinnerVerificationSerializer(winning, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        winning = self.get_object()
        winning.review_status = 'rejected'
        winning.reviewed_at = timezone.now()
        winning.admin_notes = request.data.get('admin_notes', winning.admin_notes)
        winning.save()
        return Response(WinnerVerificationSerializer(winning, context={'request': request}).data)

    @action(detail=True, methods=['post'])
    def mark_paid(self, request, pk=None):
        winning = self.get_object()
        winning.payment_status = 'paid'
        winning.save()
        return Response(WinnerVerificationSerializer(winning, context={'request': request}).data)
