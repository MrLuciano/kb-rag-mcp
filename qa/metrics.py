def hit_rate(retrieved_results, golden_answers):
    if not retrieved_results or not golden_answers:
        return 0.0
    hits = 0
    total = len(golden_answers)
    for retrieved, golden in zip(retrieved_results, golden_answers):
        if golden in retrieved:
            hits += 1
    return hits / total if total > 0 else 0.0


def mrr(retrieved_results, golden_answers):
    """Mean Reciprocal Rank."""
    if not retrieved_results or not golden_answers:
        return 0.0
    total = len(golden_answers)
    rr_sum = 0.0
    for retrieved, golden in zip(retrieved_results, golden_answers):
        for rank, chunk_id in enumerate(retrieved, start=1):
            if chunk_id == golden:
                rr_sum += 1.0 / rank
                break
    return rr_sum / total if total > 0 else 0.0


def p50_score(score_lists):
    """Median top-1 score across queries. score_lists: list of list of floats."""
    import statistics
    top_scores = [s[0] for s in score_lists if s]
    if not top_scores:
        return 0.0
    return statistics.median(top_scores)


def compute_all(retrieved_results, golden_answers, score_lists=None):
    """Return a complete metrics dict ready for render_report."""
    hr = hit_rate(retrieved_results, golden_answers)
    m = mrr(retrieved_results, golden_answers)
    zr = sum(len(r) == 0 for r in retrieved_results) / max(len(retrieved_results), 1)
    p50 = p50_score(score_lists) if score_lists else 0.0
    passed = hr >= 0.70 and m >= 0.50 and zr <= 0.10 and p50 >= 0.45
    return {
        "hit_rate": hr,
        "mrr": m,
        "zero_result_pct": zr,
        "p50_score": p50,
        "total": len(golden_answers),
        "passed": passed,
    }
