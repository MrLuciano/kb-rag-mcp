from qa.report import render_report


def test_report_minimal():
    data = {
        "hit_rate": 0.85,
        "mrr": 0.67,
        "zero_result_pct": 0.02,
        "p50_score": 0.51,
        "total": 20,
        "passed": True,
    }
    md = render_report(data)
    assert isinstance(md, str)
    assert "## KB QA Report" in md
    assert "Hit Rate: 85%" in md
    assert "MRR: 0.67" in md
    assert "PASS" in md or "FAIL" in md
    assert "Total queries: 20" in md
