from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    MySubscriptionView, start_subscription, cancel_subscription,
    reactivate_subscription, create_checkout_session, stripe_webhook,
    AdminSubscriptionViewSet,
)

router = DefaultRouter()
router.register('admin', AdminSubscriptionViewSet, basename='admin-subscriptions')

urlpatterns = [
    path('me', MySubscriptionView.as_view()),
    path('start', start_subscription),
    path('cancel', cancel_subscription),
    path('reactivate', reactivate_subscription),
    path('checkout-session', create_checkout_session),
    path('webhook', stripe_webhook),
    path('', include(router.urls)),
]
