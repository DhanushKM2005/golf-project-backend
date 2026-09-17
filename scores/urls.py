from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ScoreViewSet, AdminScoreViewSet

router = DefaultRouter()
router.register('admin', AdminScoreViewSet, basename='score-admin')
router.register('', ScoreViewSet, basename='score')

urlpatterns = [
    path('', include(router.urls)),
]
