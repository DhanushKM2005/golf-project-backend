from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenRefreshView
from accounts.views import RegisterView, LoginView, MeView
from accounts.admin_views import UserAdminViewSet
from rest_framework.routers import DefaultRouter
from draws.reports import reports_view

admin_router = DefaultRouter()
admin_router.register('admin/users', UserAdminViewSet, basename='admin-users')

urlpatterns = [
    path('django-admin/', admin.site.urls),

    path('api/auth/register', RegisterView.as_view(), name='auth-register'),
    path('api/auth/login', LoginView.as_view(), name='auth-login'),
    path('api/auth/refresh', TokenRefreshView.as_view(), name='auth-refresh'),
    path('api/auth/me', MeView.as_view(), name='auth-me'),

    path('api/subscriptions/', include('subscriptions.urls')),
    path('api/scores/', include('scores.urls')),
    path('api/charities/', include('charities.urls')),
    path('api/draws/', include('draws.urls')),
    path('api/reports/', reports_view, name='reports'),
    path('api/', include(admin_router.urls)),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
