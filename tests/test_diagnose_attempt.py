from __future__ import annotations

import failure_class
import pytest

from examples import diagnose_attempt


def test_example_uses_the_installed_classifier_api():
    assert diagnose_attempt.FailureClass is failure_class.FailureClass
    assert diagnose_attempt.classify_failure is failure_class.classify_failure


def test_teaching_fixtures_cover_provider_quality_success_and_grader_failure():
    results = diagnose_attempt.run_teaching_fixtures()

    assert [result.classification for result in results] == [
        failure_class.FailureClass.AUTH.value,
        failure_class.FailureClass.MODEL_QUALITY.value,
        failure_class.FailureClass.NONE.value,
        "grader-failure",
    ]
    assert [result.score for result in results] == [None, 0, 1, None]
    assert "outside classifier" in results[-1].next_action


def test_transport_error_is_diagnosed_and_never_credited_as_zero():
    def connection_failure() -> str:
        raise ConnectionRefusedError("connection refused")

    result = diagnose_attempt.diagnose_attempt(
        "transport-error", connection_failure, diagnose_attempt.exact_match
    )

    assert result.classification == failure_class.FailureClass.CONNECTION.value
    assert result.score is None


def test_grader_exception_stays_outside_classifier():
    def broken_grader(_: str) -> bool:
        raise ValueError("bad rubric")

    result = diagnose_attempt.diagnose_attempt(
        "grader-error", lambda: "4", broken_grader
    )

    assert result.classification == "grader-failure"
    assert result.score is None


def test_main_output_is_deterministic(capsys: pytest.CaptureFixture[str]):
    diagnose_attempt.main()
    first = capsys.readouterr().out
    diagnose_attempt.main()
    second = capsys.readouterr().out

    assert first == second
    assert first.startswith(
        "Simulated teaching fixtures; not live provider or replay evidence.\n"
    )
    assert "observation=provider-auth | classification=auth" in first
