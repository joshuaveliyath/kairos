def verify_results(results: list) -> list:
    for r in results:
        title_words = set(r['title'].lower().split())

        similar_count = sum(
            1 for other in results
            if other != r and
            len(title_words &
                set(other['title'].lower().split())) >= 2
        )

        r['verified_by'] = similar_count + 1

        if r['verified_by'] >= 4:
            r['confidence'] = "🟢 HIGHLY VERIFIED"
        elif r['verified_by'] >= 3:
            r['confidence'] = "🟡 VERIFIED"
        elif r['verified_by'] >= 2:
            r['confidence'] = "🟠 LIKELY TRUE"
        else:
            r['confidence'] = "🔴 UNVERIFIED"

    freshness_order = {
        "seconds": 0,
        "minutes": 1,
        "Recent": 2
    }
    results.sort(key=lambda x: (
        -x['verified_by'],
        freshness_order.get(x['freshness'], 3)
    ))

    return results