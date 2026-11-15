"""Transparent advice derived only from eligible observations, never placeholder stats."""
from datetime import datetime, timezone, timedelta
from math import isfinite
from statistics import median


def instant(value):
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace('Z', '+00:00'))
    # SQL session is explicitly UTC; connector TIMESTAMP values can be naive.
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def eligible(rows, demo=False, current=False, now=None):
    now = now or datetime.now(timezone.utc)
    result = []
    for row in rows:
        try:
            price = float(row['price'])
            stamp = instant(row['observed_at'])
            if isinstance(row['price'], bool) or not isfinite(price) or price <= 0:
                continue
            if row['match_type'] != 'exact' or row['currency'] != 'USD' or stamp > now:
                continue
            if row['source_type'] not in (('demo',) if demo else ('snapshot', 'live')):
                continue
            if current and stamp < now - timedelta(hours=24):
                continue
            result.append({**row, 'price': price, 'observed_at': stamp})
        except (KeyError, TypeError, ValueError, AttributeError):
            continue
    if current:
        latest = {}
        for row in sorted(result, key=lambda r: (r['observed_at'], r['offer_id'])):
            latest[(row['retailer'].strip().casefold(), row['currency'])] = row
        result = list(latest.values())
    return sorted(result, key=lambda r: (r['price'], r['retailer']) if current else (r['observed_at'], r['offer_id']))


def coverage(rows):
    times = [r['observed_at'] for r in rows]
    return {'observation_count': len(rows), 'distinct_observation_dates': len({t.date() for t in times}),
            'span_hours': (max(times)-min(times)).total_seconds()/3600 if times else 0,
            'first_observed_at': min(times) if times else None, 'last_observed_at': max(times) if times else None}


def advise(product, history, current):
    demo = product['data_status'] == 'demo'
    history = eligible(history, demo=demo)
    current = eligible(current, demo=demo, current=True)
    cov = coverage(history)
    current_price = min((r['price'] for r in current), default=None)
    historical_median = median([r['price'] for r in history]) if history else None
    result = {'product_id': product['product_id'], 'decision': 'INSUFFICIENT_DATA',
              'explanation': 'Need a fresh reviewed offer and at least 3 UTC observation dates spanning 48 hours.',
              'evidence': [{**cov, 'current_lowest_price': current_price, 'median_observed_price': historical_median}],
              'data_status': 'demo' if demo else 'insufficient'}
    if demo:
        result['explanation'] = 'Illustrative demo data never qualifies for real buying advice.'
    elif current_price is not None and historical_median is not None and cov['distinct_observation_dates'] >= 3 and cov['span_hours'] >= 48:
        buy = current_price <= historical_median * 0.9
        result.update(decision='BUY' if buy else 'WAIT_OR_COMPARE', data_status='observed',
                      explanation=('Current reviewed price is at least 10% below the observed median. ' if buy else
                                   'Current reviewed price is not at least 10% below the observed median; compare other options. ')
                                  + 'This is a simple price-history heuristic, not a forecast or guarantee.')
    return result
