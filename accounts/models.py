from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Role is derived from Django's built-in flags rather than a duplicate
    field: is_staff/is_superuser => Administrator, everyone else with a
    verified account => Registered subscriber. Anonymous browsing needs
    no model at all (ROLE 01 in the PRD is just "no auth required").
    """
    phone = models.CharField(max_length=20, blank=True)

    @property
    def role(self):
        return 'admin' if self.is_staff else 'subscriber'
