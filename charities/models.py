from django.conf import settings
from django.db import models


class Charity(models.Model):
    CATEGORY_CHOICES = [
        ('health', 'Healthcare & Medical'),
        ('youth', 'Youth & Education'),
        ('environment', 'Environment & Conservation'),
        ('veterans', 'Veterans & First Responders'),
        ('community', 'Community Development'),
        ('sports', 'Sports & Inclusivity'),
    ]

    name = models.CharField(max_length=200)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default='community')
    tagline = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    image_url = models.URLField(blank=True)
    image = models.ImageField(upload_to='charities/', blank=True, null=True)
    website_url = models.URLField(blank=True)
    is_featured = models.BooleanField(default=False)  # PRD §08.2 Homepage Spotlight
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = 'charities'
        ordering = ['-is_featured', 'name']

    def __str__(self):
        return self.name


class CharityEvent(models.Model):
    """
    PRD §08.2: Upcoming events such as charity golf days.
    """
    charity = models.ForeignKey(Charity, related_name='events', on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    location = models.CharField(max_length=200, blank=True)
    event_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['event_date']

    def __str__(self):
        return f'{self.title} ({self.charity.name})'


class Donation(models.Model):
    """
    PRD §08.1: Independent donation option, not tied to gameplay.
    Open to public visitors as well as registered subscribers.
    """
    charity = models.ForeignKey(Charity, related_name='donations', on_delete=models.CASCADE)
    donor_user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    donor_name = models.CharField(max_length=150)
    donor_email = models.EmailField(blank=True)
    amount = models.PositiveIntegerField()  # Amount in INR
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'₹{self.amount} to {self.charity.name} by {self.donor_name}'
