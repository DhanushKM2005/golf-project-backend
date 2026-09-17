from django.contrib.auth import get_user_model
from django.db.models import Sum, Count
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from subscriptions.models import Subscription
from charities.models import Charity, Donation
from .models import Draw, WinnerVerification

User = get_user_model()


@api_view(['GET'])
@permission_classes([IsAdminUser])
def reports_view(request):
    """
    PRD §11.05 Admin Reports & Analytics:
    - Total users & active subscribers
    - Total prize pool paid out
    - Current jackpot rollover
    - Charity contribution totals (subscription percentage share + independent donations)
    - Draw statistics and tier winner counts
    """
    active_subs = Subscription.objects.filter(status='active').select_related('charity')
    published_draws = Draw.objects.filter(status='published').order_by('-year', '-month')

    # Charity contribution breakdown
    charity_totals = []
    total_subscription_charity = 0
    for c in Charity.objects.all():
        subs = [s for s in active_subs if s.charity_id == c.id]
        sub_est = sum(s.fee * s.charity_percentage / 100 for s in subs)
        donations_sum = Donation.objects.filter(charity=c).aggregate(total=Sum('amount'))['total'] or 0
        total_subscription_charity += sub_est
        charity_totals.append({
            'charity_id': c.id,
            'charity': c.name,
            'category': c.get_category_display(),
            'subscriber_count': len(subs),
            'subscription_contributions': round(sub_est, 2),
            'independent_donations': donations_sum,
            'total_raised': round(sub_est + donations_sum, 2),
        })

    # Independent donations total
    total_independent = Donation.objects.aggregate(total=Sum('amount'))['total'] or 0

    # Prize pool & winners metrics
    total_prize_paid = WinnerVerification.objects.filter(payment_status='paid').aggregate(total=Sum('prize_amount'))['total'] or 0
    total_prize_awarded = WinnerVerification.objects.aggregate(total=Sum('prize_amount'))['total'] or 0
    pending_payouts = WinnerVerification.objects.filter(payment_status='pending').aggregate(total=Sum('prize_amount'))['total'] or 0

    latest_draw = published_draws.first()
    current_rollover = latest_draw.jackpot_rollover_out if latest_draw else 0

    # Draw stats per tier
    winners_by_tier = {
        '5_match': WinnerVerification.objects.filter(match_count=5).count(),
        '4_match': WinnerVerification.objects.filter(match_count=4).count(),
        '3_match': WinnerVerification.objects.filter(match_count=3).count(),
    }

    return Response({
        'total_users': User.objects.count(),
        'active_subscribers': active_subs.count(),
        'total_prize_pool_awarded': total_prize_awarded,
        'total_prize_pool_paid_out': total_prize_paid,
        'pending_payouts_amount': pending_payouts,
        'current_jackpot_rollover': current_rollover,
        'total_charity_raised': round(total_subscription_charity + total_independent, 2),
        'charity_subscription_share': round(total_subscription_charity, 2),
        'charity_independent_donations': total_independent,
        'charity_contribution_totals': charity_totals,
        'draws_published': published_draws.count(),
        'winners_by_tier': winners_by_tier,
    })
