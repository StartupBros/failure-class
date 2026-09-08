# failure-class

One enum and one classifier for the question every LLM eval and serving stack
hits: **did the model fail, or did everything around it?**

Stdlib only. Python ≥ 3.11. MIT.

## Why

When an eval sample comes back empty, "the model scored zero" and "the runtime
wedged" are different facts with different owners. Blaming quality for infra
failures corrupts benchmark data; blaming infra for quality misses hides real
regressions. `classify_failure` assigns one primary failure class with explicit
precedence, and deliberately refuses to collapse a scorer miss after a
successful response into a provider failure.

## Classes

| Class | Meaning |
| --- | --- |
| `NONE` | No failure detected. |
| `CONNECTION` | Endpoint unreachable: refused, DNS, network. |
| `AUTH` | 401/403 or auth-marker text. |
| `CONTEXT_OR_MODEL_FIT` | Prompt or model does not fit: context window, out of memory. |
| `ENDPOINT_PROTOCOL` | The endpoint answered with a malformed or unexpected shape. |
| `TIMEOUT_SLA` | Timeout or SLA breach: 408/429/504, timeout exceptions. |
| `HARNESS_ABORT` | The harness cancelled, aborted, or limit-stopped the attempt. |
| `RUNTIME_PROVIDER_WEDGED` | The serving runtime is unhealthy or wedged; any 5xx. |
| `MODEL_QUALITY` | The model responded; the output failed scoring. |

## Use

```python
from failure_class import FailureClass, classify_failure

try:
    response = call_endpoint(...)
except Exception as exc:
    cls = classify_failure(exc)

classify_failure(status_code=401, message="unauthorized")
# FailureClass.AUTH

classify_failure(successful_model_response=True, scorer_failed=True)
# FailureClass.MODEL_QUALITY — a scored miss is never an infra failure
```

For a runnable local walkthrough from the repository root:

```console
$ python3 -m examples.diagnose_attempt
Simulated teaching fixtures; not live provider or replay evidence.
observation=provider-auth | classification=auth | score=not-recorded | next_action=fix provider access; do not score
observation=wrong-answer | classification=model-quality | score=0 | next_action=inspect model quality; record score 0
observation=correct-answer | classification=none | score=1 | next_action=record successful score 1
observation=grader-error | classification=grader-failure | score=not-recorded | next_action=fix grader outside classifier; do not score
```

These are deterministic teaching fixtures, not observations from a provider or
replay. The grader exception is handled explicitly outside `classify_failure`.

Precedence (highest first): model-quality-after-success, auth, timeout,
connection, protocol, context/fit, wedged, abort, bare 5xx → wedged,
scorer-failed alone → model-quality, none. HTTP status codes and exception
types outrank text markers when both are present.

## Install

```
pip install git+https://github.com/StartupBros/failure-class
```

## Origin

Extracted from a private eval lab, where it triages local-endpoint runs
(`mlx_lm.server`, llama.cpp `llama-server`) in benchmark pipelines. The class
string values are stable identifiers used in stored eval evidence; they will
not be renamed.
