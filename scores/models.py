from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


class Score(models.Model):
    """One Stableford round. §05: only the latest 5 per user are kept,
    one entry per date, range 1-45. Enforcement lives in the serializer
    (uniqueness + rolling window) rather than only in the DB, so the API
    can return a clear validation error instead of an IntegrityError."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='scores')
    value = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(45)])
    played_on = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-played_on']
        unique_together = ('user', 'played_on')
