from django.conf import settings
from django.db import models


class Draw(models.Model):
    TYPE_CHOICES = [('random', 'Random'), ('algorithmic', 'Algorithmic')]
    STATUS_CHOICES = [('draft', 'Draft'), ('simulated', 'Simulated'), ('published', 'Published')]

    month = models.PositiveSmallIntegerField()
    year = models.PositiveSmallIntegerField()
    draw_type = models.CharField(max_length=15, choices=TYPE_CHOICES, default='random')
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='draft')

    winning_numbers = models.JSONField(default=list, blank=True)  # 5 numbers, 1-45
    jackpot_rollover_in = models.PositiveIntegerField(default=0)  # carried into this draw's 5-match pool
    jackpot_rollover_out = models.PositiveIntegerField(default=0)  # carried out if 5-match unclaimed
    pool_breakdown = models.JSONField(default=dict, blank=True)  # {"5": amt, "4": amt, "3": amt}
    total_pool = models.PositiveIntegerField(default=0)

    # Simulation caching fields (PRD §06: "Simulation before publish")
    simulated_numbers = models.JSONField(default=list, blank=True)
    simulated_pool = models.PositiveIntegerField(default=0)
    simulated_breakdown = models.JSONField(default=dict, blank=True)
    simulated_rollover_out = models.PositiveIntegerField(default=0)
    simulated_winners = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('month', 'year')
        ordering = ['-year', '-month']

    def __str__(self):
        return f'Draw {self.month}/{self.year} ({self.status})'

    def save(self, *args, **kwargs):
        # Auto-carry forward jackpot rollover from prior published draw if not specified
        if not self.pk and self.jackpot_rollover_in == 0:
            last_draw = Draw.objects.filter(status='published').order_by('-year', '-month').first()
            if last_draw and last_draw.jackpot_rollover_out > 0:
                self.jackpot_rollover_in = last_draw.jackpot_rollover_out
        super().save(*args, **kwargs)


class DrawEntry(models.Model):
    """
    PRD §06 / §07:
    A subscriber's ticket for one draw: the distinct Stableford values
    from their 5 most recent scores at draw time.
    """
    draw = models.ForeignKey(Draw, on_delete=models.CASCADE, related_name='entries')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    numbers = models.JSONField(default=list)
    match_count = models.PositiveSmallIntegerField(default=0)

    class Meta:
        unique_together = ('draw', 'user')

    def __str__(self):
        return f'{self.user.username} in {self.draw} ({self.match_count} matches)'


class WinnerVerification(models.Model):
    """
    PRD §09 Winner Verification System:
    - Eligibility: Verification process applies to winners only
    - Proof upload: Screenshot of scores from the golf platform
    - Admin review: Approve or reject submission
    - Payment states: Pending -> Paid
    """
    PAYMENT_CHOICES = [('pending', 'Pending'), ('paid', 'Paid')]
    REVIEW_CHOICES = [('pending', 'Pending review'), ('approved', 'Approved'), ('rejected', 'Rejected')]

    draw = models.ForeignKey(Draw, on_delete=models.CASCADE, related_name='winners')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='winnings')
    match_count = models.PositiveSmallIntegerField()
    prize_amount = models.PositiveIntegerField(default=0)
    proof_image = models.ImageField(upload_to='winner_proofs/', blank=True, null=True)
    proof_image_url = models.URLField(blank=True)
    review_status = models.CharField(max_length=15, choices=REVIEW_CHOICES, default='pending')
    payment_status = models.CharField(max_length=10, choices=PAYMENT_CHOICES, default='pending')
    admin_notes = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username} - {self.match_count}-match - ₹{self.prize_amount} ({self.review_status})'
