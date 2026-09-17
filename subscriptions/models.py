from django.conf import settings
from django.db import models
from django.utils import timezone
from datetime import timedelta
from charities.models import Charity


class Subscription(models.Model):
    PLAN_CHOICES = [('monthly', 'Monthly'), ('yearly', 'Yearly')]
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('cancelled', 'Cancelled'),
        ('lapsed', 'Lapsed'),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='subscription')
    plan = models.CharField(max_length=10, choices=PLAN_CHOICES)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    charity = models.ForeignKey(Charity, on_delete=models.SET_NULL, null=True, related_name='subscribers')
    charity_percentage = models.PositiveIntegerField(default=10)  # >= MIN_CHARITY_PERCENT, enforced in serializer
    started_at = models.DateTimeField(auto_now_add=True)
    renews_at = models.DateTimeField()
    stripe_customer_id = models.CharField(max_length=100, blank=True)
    stripe_subscription_id = models.CharField(max_length=100, blank=True)

    @property
    def fee(self):
        return settings.YEARLY_FEE if self.plan == 'yearly' else settings.MONTHLY_FEE

    def mark_renewed(self):
        days = 365 if self.plan == 'yearly' else 30
        self.renews_at = timezone.now() + timedelta(days=days)
        self.status = 'active'
        self.save()

    def check_lapsed(self):
        if self.status == 'active' and timezone.now() > self.renews_at:
            self.status = 'lapsed'
            self.save()
        return self.status
