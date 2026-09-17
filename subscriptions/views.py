from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import stripe
from rest_framework import generics, permissions, viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, action
from rest_framework.permissions import IsAdminUser, AllowAny, IsAuthenticated
from .models import Subscription
from .serializers import SubscriptionSerializer

if getattr(settings, 'STRIPE_SECRET_KEY', None):
    stripe.api_key = settings.STRIPE_SECRET_KEY


class MySubscriptionView(generics.RetrieveUpdateAPIView):
    """
    GET/PATCH the caller's own subscription (PRD §04, §10).
    Performs real-time check_lapsed() validation.
    """
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        sub, _ = Subscription.objects.get_or_create(
            user=self.request.user,
            defaults={
                'plan': 'monthly',
                'renews_at': timezone.now() + timedelta(days=30),
                'charity_percentage': settings.MIN_CHARITY_PERCENT,
            },
        )
        sub.check_lapsed()
        return sub


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def start_subscription(request):
    """
    Start or change subscription plan (Monthly ₹999 or Yearly ₹9,999).
    Immediately activates with real renewal timeframe.
    """
    plan = request.data.get('plan', 'monthly')
    if plan not in ('monthly', 'yearly'):
        return Response({'error': 'Invalid plan. Choose monthly or yearly.'}, status=status.HTTP_400_BAD_REQUEST)

    days = 365 if plan == 'yearly' else 30
    sub, _ = Subscription.objects.get_or_create(
        user=request.user,
        defaults={'plan': plan, 'charity_percentage': settings.MIN_CHARITY_PERCENT}
    )
    sub.plan = plan
    sub.status = 'active'
    sub.renews_at = timezone.now() + timedelta(days=days)
    sub.save()
    return Response(SubscriptionSerializer(sub).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_subscription(request):
    """
    Cancels the caller's subscription.
    """
    sub = Subscription.objects.filter(user=request.user).first()
    if sub:
        sub.status = 'cancelled'
        sub.save()
        return Response(SubscriptionSerializer(sub).data)
    return Response({'error': 'No subscription found.'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def reactivate_subscription(request):
    """
    Reactivates a cancelled or lapsed subscription.
    """
    sub = Subscription.objects.filter(user=request.user).first()
    if not sub:
        return Response({'error': 'No subscription found.'}, status=status.HTTP_404_NOT_FOUND)
    days = 365 if sub.plan == 'yearly' else 30
    sub.status = 'active'
    sub.renews_at = timezone.now() + timedelta(days=days)
    sub.save()
    return Response(SubscriptionSerializer(sub).data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_checkout_session(request):
    """
    PRD §04 Stripe Gateway Integration:
    Creates a Stripe Checkout Session or provides PCI-compliant fallback/mock.
    """
    plan = request.data.get('plan', 'monthly')
    fee = settings.YEARLY_FEE if plan == 'yearly' else settings.MONTHLY_FEE
    stripe_key = getattr(settings, 'STRIPE_SECRET_KEY', '')

    # If real Stripe key is configured and not mock test key
    if stripe_key and not stripe_key.startswith('sk_test_mock'):
        try:
            domain = request.build_absolute_uri('/')[:-1]
            session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'inr',
                        'product_data': {
                            'name': f'Digital Heroes Golf Subscription ({plan.capitalize()})',
                            'description': f'Includes Stableford draw participation + 10%+ charity contribution',
                        },
                        'unit_amount': fee * 100,
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=f'{domain}/dashboard?session_id={{CHECKOUT_SESSION_ID}}',
                cancel_url=f'{domain}/dashboard?cancelled=true',
                client_reference_id=str(request.user.id),
                customer_email=request.user.email or None,
            )
            return Response({'sessionId': session.id, 'url': session.url})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    # Simulated/Test Checkout Session
    days = 365 if plan == 'yearly' else 30
    sub, _ = Subscription.objects.get_or_create(user=request.user, defaults={'plan': plan})
    sub.plan = plan
    sub.status = 'active'
    sub.renews_at = timezone.now() + timedelta(days=days)
    sub.save()
    return Response({
        'simulated': True,
        'message': 'Simulated PCI-compliant payment confirmed.',
        'subscription': SubscriptionSerializer(sub).data
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def stripe_webhook(request):
    """
    PRD §04 Stripe Webhook listener:
    Processes asynchronous subscription renewals, payments, and cancellations.
    """
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')
    webhook_secret = getattr(settings, 'STRIPE_WEBHOOK_SECRET', '')

    event = None
    if webhook_secret and not webhook_secret.startswith('whsec_mock'):
        try:
            event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    else:
        event = request.data

    event_type = event.get('type') if isinstance(event, dict) else getattr(event, 'type', '')
    data_obj = event.get('data', {}).get('object', {}) if isinstance(event, dict) else getattr(event, 'data', {}).get('object', {})

    if event_type == 'checkout.session.completed':
        user_id = data_obj.get('client_reference_id')
        if user_id:
            sub = Subscription.objects.filter(user_id=user_id).first()
            if sub:
                sub.mark_renewed()

    return Response({'received': True})


class AdminSubscriptionViewSet(viewsets.ModelViewSet):
    """
    PRD §11.01 Admin Subscription Management:
    Allows administrators to list, inspect, filter, and modify user subscriptions.
    """
    queryset = Subscription.objects.all().select_related('user', 'charity')
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        qs = super().get_queryset()
        status_param = self.request.query_params.get('status')
        if status_param:
            qs = qs.filter(status=status_param)
        plan_param = self.request.query_params.get('plan')
        if plan_param:
            qs = qs.filter(plan=plan_param)
        return qs
