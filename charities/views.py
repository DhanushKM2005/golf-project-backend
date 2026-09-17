from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Charity, CharityEvent, Donation
from .serializers import CharitySerializer, CharityEventSerializer, DonationSerializer


class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_staff)


class CharityViewSet(viewsets.ModelViewSet):
    """
    PRD §08 Charity Directory & §11.03 Charity Management:
    - Public search & filter (by search query, category, featured status)
    - Full CRUD gated to admins
    - Charity details with upcoming golf days/events
    """
    serializer_class = CharitySerializer
    permission_classes = [IsAdminOrReadOnly]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name', 'tagline', 'description']

    def get_queryset(self):
        qs = Charity.objects.all() if (self.request.user and self.request.user.is_staff) else Charity.objects.filter(is_active=True)

        featured = self.request.query_params.get('is_featured')
        if featured is not None:
            qs = qs.filter(is_featured=featured.lower() == 'true')

        category = self.request.query_params.get('category')
        if category:
            qs = qs.filter(category=category)

        return qs.prefetch_related('events', 'subscribers')


class CharityEventViewSet(viewsets.ModelViewSet):
    """
    PRD §08.2 / §11.03:
    Manage charity events such as golf days and tournaments.
    """
    queryset = CharityEvent.objects.all().select_related('charity')
    serializer_class = CharityEventSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        qs = super().get_queryset()
        charity_id = self.request.query_params.get('charity')
        if charity_id:
            qs = qs.filter(charity_id=charity_id)
        return qs


class DonationViewSet(viewsets.ModelViewSet):
    """
    PRD §08.1 Independent donation option, not tied to gameplay:
    Anyone (public visitor or logged in subscriber) can submit a donation.
    Admins can view and filter all donations.
    """
    queryset = Donation.objects.all().select_related('charity', 'donor_user')
    serializer_class = DonationSerializer

    def get_permissions(self):
        if self.action in ('create',):
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(donor_user=user)
