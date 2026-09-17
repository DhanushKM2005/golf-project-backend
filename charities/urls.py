from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CharityViewSet, CharityEventViewSet, DonationViewSet

router = DefaultRouter()
router.register('events', CharityEventViewSet, basename='charity-events')
router.register('donations', DonationViewSet, basename='charity-donations')
router.register('', CharityViewSet, basename='charity')

urlpatterns = [
    path('', include(router.urls)),
]
