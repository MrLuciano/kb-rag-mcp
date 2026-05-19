def render_report(data):
    hit_rate_pct = int(round(data["hit_rate"] * 100))
    verdict = "PASS" if data.get("passed") else "FAIL"
    return f"""## OTCS KB QA Report\n\nHit Rate: {hit_rate_pct}%\nMRR: {data['mrr']:.2f}\nZero-result percentage: {int(round(data['zero_result_pct']*100))}%\nScore p50: {data['p50_score']:.2f}\n\nTotal queries: {data['total']}\n\nOverall verdict: **{verdict}**\n"""
