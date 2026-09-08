"""Runnable failure-class teaching fixtures; no network or live evidence."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from failure_class import FailureClass, classify_failure


@dataclass(frozen=True)
class Diagnosis:
    observation: str
    classification: str
    score: int | None
    next_action: str


def exact_match(response: str) -> bool:
    """A deliberately simple deterministic scorer for the expected answer 4."""
    return response.strip() == "4"


def diagnose_attempt(
    observation: str,
    call_endpoint: Callable[[], str],
    grader: Callable[[str], bool],
) -> Diagnosis:
    try:
        response = call_endpoint()
    except Exception as exc:
        failure = classify_failure(exc)
        return Diagnosis(
            observation, failure.value, None, "fix provider access; do not score"
        )

    try:
        scorer_failed = not grader(response)
    except Exception:
        return Diagnosis(
            observation,
            "grader-failure",
            None,
            "fix grader outside classifier; do not score",
        )

    failure = classify_failure(
        successful_model_response=True, scorer_failed=scorer_failed
    )
    if failure is FailureClass.MODEL_QUALITY:
        action = "inspect model quality; record score 0"
        score = 0
    else:
        action = "record successful score 1"
        score = 1
    return Diagnosis(observation, failure.value, score, action)


class TeachingAuthError(Exception):
    status_code = 401


def _auth_failure() -> str:
    raise TeachingAuthError("bad credentials")


def _grader_failure(_: str) -> bool:
    raise ValueError("teaching grader failure")


def run_teaching_fixtures() -> list[Diagnosis]:
    return [
        diagnose_attempt("provider-auth", _auth_failure, exact_match),
        diagnose_attempt("wrong-answer", lambda: "5", exact_match),
        diagnose_attempt("correct-answer", lambda: "4", exact_match),
        diagnose_attempt("grader-error", lambda: "4", _grader_failure),
    ]


def main() -> None:
    print("Simulated teaching fixtures; not live provider or replay evidence.")
    for result in run_teaching_fixtures():
        score = "not-recorded" if result.score is None else result.score
        print(
            f"observation={result.observation} | classification={result.classification} "
            f"| score={score} | next_action={result.next_action}"
        )


if __name__ == "__main__":
    main()
