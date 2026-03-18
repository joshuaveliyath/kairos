from core.memory import get_source_reputation

# Default score is managed natively by get_source_reputation (50/100).
# No longer using hardcoded SOURCE_BASE_WEIGHTS. Anyone can gain reputation now.
def verify_results(results: list) -> tuple[list, int]:
    max_weight_found = 0.0
    
    for r in results:
        title_words = set(r['title'].lower().split())

        # 💀 All sources are stored globally and weighed dynamically.
        # Calling get_source_reputation will return 50 if new, or their stored rep.
        reputation = get_source_reputation(r['source'])
        rep_multiplier = reputation / 50.0  # 50 is base, so 1.0x. 100 is 2.0x.
        
        base_weight = 1.0 * rep_multiplier
        
        similar_weight = 0
        for other in results:
            if other != r and len(title_words & set(other['title'].lower().split())) >= 2:
                other_rep = get_source_reputation(other['source'])
                other_mult = other_rep / 50.0
                similar_weight += 1.0 * other_mult

        total_weight = base_weight + similar_weight
        r['verified_by_weight'] = total_weight
        
        if total_weight > max_weight_found:
            max_weight_found = total_weight

        if total_weight >= 6.0:
            r['confidence'] = "🟢 HIGHLY VERIFIED"
        elif total_weight >= 4.0:
            r['confidence'] = "🟡 VERIFIED"
        elif total_weight >= 2.0:
            r['confidence'] = "🟠 LIKELY TRUE"
        else:
            r['confidence'] = "🔴 UNVERIFIED"

    freshness_order = {
        "seconds": 0,
        "minutes": 1,
        "Recent": 2
    }
    
    results.sort(key=lambda x: (
        -x.get('verified_by_weight', 0),
        freshness_order.get(x.get('freshness', 'Recent'), 3)
    ))

    # 💀 Tier 4: Freshness Decay Indicator
    for r in results:
        f = r.get('freshness', 'Recent')
        if f == "seconds":
            r['freshness_tag'] = "🟢 Just now"
        elif f == "minutes":
            r['freshness_tag'] = "🟢 Very fresh"
        elif f == "hours":
            r['freshness_tag'] = "🟡 Today"
        elif f == "days":
            r['freshness_tag'] = "🔴 Older"
        else:
            r['freshness_tag'] = "⚪ Unknown"

    # 💀 Tier 3: Confidence scoring visible
    # Calculate a percentage score (cap at 99%, reserve 100 for absolute certainty)
    overall_confidence = min(99, int((max_weight_found / 10.0) * 100)) if results else 0

    return results, overall_confidence