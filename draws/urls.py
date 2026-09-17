from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import DrawViewSet, PublicDrawViewSet, MyDrawEntriesView, WinnerVerificationViewSet

router = DefaultRouter()
router.register('admin', DrawViewSet, basename='draw-admin')
router.register('public', PublicDrawViewSet, basename='draw-public')
router.register('my-entries', MyDrawEntriesView, basename='my-entries')
router.register('winners', WinnerVerificationViewSet, basename='winner')

urlpatterns = [
    path('', include(router.urls)),
]
