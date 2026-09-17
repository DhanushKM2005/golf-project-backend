"""
Draw engine — PRD §06/§07.

- Random draw: 5 unique numbers, uniform from 1-45.
- Algorithmic draw: 5 unique numbers, weighted by frequency of Stableford scores
  across all subscribers' latest rounds.
- Prize distribution:
    5-number = 40% (rolls over if unclaimed)
    4-number = 35%
    3-number = 25%
- Equal prize splitting among winners in the same tier.
- Simulation before publish: Simulated numbers & pools are cached so that publishing
  commits the exact approved simulation.
"""
import random
from collections import Counter
from django.conf import settings
from scores.models import Score
from subscriptions.models import Subscription
from .models import Draw, DrawEntry, WinnerVerification


def _ticket_for(user):
    """
    Ticket numbers are the distinct Stableford values from the user's latest 5 scores.
    """
    values = list(
        Score.objects.filter(user=user)
        .order_by('-played_on')[:5]
        .values_list('value', flat=True)
    )
    return set(values)


def _draw_numbers(draw_type):
    pool = list(range(1, 46))
    if draw_type == 'algorithmic':
        freq = Counter(Score.objects.values_list('value', flat=True))
        weights = [freq.get(n, 0) + 1 for n in pool]  # +1 so unplayed numbers remain possible
        numbers = set()
        choices, w = pool[:], weights[:]
        while len(numbers) < 5 and choices:
            pick = random.choices(choices, weights=w, k=1)[0]
            numbers.add(pick)
            idx = choices.index(pick)
            choices.pop(idx)
            w.pop(idx)
        return sorted(numbers)
    return sorted(random.sample(pool, 5))


def _compute_pool(active_count, rollover_in):
    total = int(active_count * settings.MONTHLY_FEE * settings.PRIZE_POOL_PERCENT_OF_FEE / 100)
    breakdown = {str(k): int(total * v) for k, v in settings.POOL_SHARE.items()}
    breakdown['5'] += rollover_in
    return total + rollover_in, breakdown


def simulate_draw(draw):
    """
    Runs the full draw against current data WITHOUT publishing.
    Caches the simulated numbers on the Draw instance so an admin can
    preview and then publish these exact results (§06 'Simulation before publish').
    """
    active_subs = list(
        Subscription.objects.filter(status='active').select_related('user')
    )
    numbers = _draw_numbers(draw.draw_type)
    total, breakdown = _compute_pool(len(active_subs), draw.jackpot_rollover_in)

    results_by_tier = {5: [], 4: [], 3: []}
    for sub in active_subs:
        ticket = _ticket_for(sub.user)
        matches = len(ticket & set(numbers))
        if matches in results_by_tier:
            results_by_tier[matches].append(sub.user)

    rollover_out = breakdown['5'] if not results_by_tier[5] else 0

    winners_by_tier_data = {
        str(tier): [
            {'id': u.id, 'username': u.username, 'email': u.email}
            for u in users
        ]
        for tier, users in results_by_tier.items()
    }

    # Cache on the draw instance
    draw.simulated_numbers = numbers
    draw.simulated_pool = total
    draw.simulated_breakdown = breakdown
    draw.simulated_rollover_out = rollover_out
    draw.simulated_winners = winners_by_tier_data
    draw.status = 'simulated'
    draw.save()

    return {
        'draw_id': draw.id,
        'winning_numbers': numbers,
        'total_pool': total,
        'pool_breakdown': breakdown,
        'rollover_in': draw.jackpot_rollover_in,
        'rollover_out': rollover_out,
        'active_subscribers_count': len(active_subs),
        'winners_by_tier': winners_by_tier_data,
        'winners_count': {str(t): len(u) for t, u in results_by_tier.items()},
    }


def publish_draw(draw, winning_numbers=None):
    """
    Persists the draw outcome: locks in winning numbers, creates
    WinnerVerification rows (pending review, §09), and splits each tier's
    pool equally among that tier's winners (§07).
    Reuses cached simulation if available to guarantee consistency.
    """
    active_subs = list(
        Subscription.objects.filter(status='active').select_related('user')
    )

    if winning_numbers:
        numbers = sorted(winning_numbers)
        total, breakdown = _compute_pool(len(active_subs), draw.jackpot_rollover_in)
    elif draw.simulated_numbers:
        numbers = draw.simulated_numbers
        total, breakdown = _compute_pool(len(active_subs), draw.jackpot_rollover_in)
    else:
        sim = simulate_draw(draw)
        numbers = sim['winning_numbers']
        total, breakdown = sim['total_pool'], sim['pool_breakdown']

    # Match tickets in one efficient pass
    user_matches = {}
    tier_winners = {5: [], 4: [], 3: []}

    for sub in active_subs:
        ticket = _ticket_for(sub.user)
        matches = len(ticket & set(numbers))
        user_matches[sub.user_id] = (ticket, matches, sub.user)
        if matches in tier_winners:
            tier_winners[matches].append(sub.user)

    rollover_out = breakdown['5'] if not tier_winners[5] else 0

    draw.winning_numbers = numbers
    draw.total_pool = total
    draw.pool_breakdown = breakdown
    draw.jackpot_rollover_out = rollover_out
    draw.status = 'published'
    draw.save()

    # Create DrawEntry tickets
    for user_id, (ticket, matches, user) in user_matches.items():
        DrawEntry.objects.update_or_create(
            draw=draw,
            user=user,
            defaults={'numbers': sorted(ticket), 'match_count': matches},
        )

    # Distribute prizes and generate winner verification records
    for tier, winners in tier_winners.items():
        if not winners:
            continue
        tier_pool = breakdown.get(str(tier), 0)
        # Split prize equally among multiple winners
        per_winner_prize = int(tier_pool / len(winners))

        for winner in winners:
            WinnerVerification.objects.update_or_create(
                draw=draw,
                user=winner,
                defaults={
                    'match_count': tier,
                    'prize_amount': per_winner_prize,
                },
            )

    return draw
