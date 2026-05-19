from qwenpaw.enterprise.readiness.checks import summarize_readiness
from qwenpaw.enterprise.readiness.models import ReadinessCheck


def test_summarize_readiness_marks_degraded_when_optional_warn():
    """必填通过但可选缺失 = degraded"""
    checks = [
        ReadinessCheck(name="database", status="pass", required=True),
        ReadinessCheck(name="redis", status="pass", required=True),
        ReadinessCheck(name="sso", status="warn", required=False),
    ]

    summary = summarize_readiness(checks)

    assert summary.status == "degraded"
    assert summary.blockers == []


def test_summarize_readiness_marks_ready_when_all_pass():
    """所有检查通过 = ready"""
    checks = [
        ReadinessCheck(name="database", status="pass", required=True),
        ReadinessCheck(name="redis", status="pass", required=True),
        ReadinessCheck(name="sso", status="pass", required=False),
    ]

    summary = summarize_readiness(checks)

    assert summary.status == "ready"
    assert summary.blockers == []


def test_summarize_readiness_marks_blocked_when_required_fails():
    checks = [
        ReadinessCheck(name="database", status="fail", required=True, message="missing"),
        ReadinessCheck(name="redis", status="pass", required=True),
    ]

    summary = summarize_readiness(checks)

    assert summary.status == "blocked"
    assert summary.blockers == ["database"]
