"""Guided questionnaire helpers for Phase 4.

This module centralizes defaults and validation behavior for
integration decision inputs captured from the UI.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from contracts import (
    BACKOFF_STRATEGIES,
    CONFLICT_STRATEGIES,
    ERROR_STRATEGIES,
    GOALS,
    LATENCY_SLOS,
    PII_HANDLING_MODES,
    SOURCE_OF_TRUTH,
    SYNC_DIRECTIONS,
    TRIGGER_MODES,
    validate_integration_answers,
)


def get_questionnaire_defaults() -> Dict[str, Any]:
    """Return default questionnaire values for a first-run session."""
    return {
        "goal": "sync",
        "source_of_truth": "api_a",
        "sync_direction": "a_to_b",
        "trigger_mode": "event",
        "latency_slo": "near_realtime",
        "conflict_strategy": "source_priority",
        "error_strategy": "retry_then_dlq",
        "retry_policy": {"max_retries": 3, "backoff": "exponential"},
        "idempotency": True,
        "pii_handling": "mask",
        "ownership_notes": "",
    }


def merge_with_defaults(raw_answers: Dict[str, Any] | None) -> Dict[str, Any]:
    """Merge potentially partial answers with defaults."""
    merged = get_questionnaire_defaults()
    if not isinstance(raw_answers, dict):
        return merged

    merged.update({k: v for k, v in raw_answers.items() if k != "retry_policy"})

    retry_policy = raw_answers.get("retry_policy")
    if isinstance(retry_policy, dict):
        merged_retry = dict(merged.get("retry_policy", {}))
        merged_retry.update(retry_policy)
        merged["retry_policy"] = merged_retry

    return merged


def validate_questionnaire_answers(answers: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate questionnaire answers against canonical contract + UX checks."""
    merged = merge_with_defaults(answers)
    is_valid, errors = validate_integration_answers(merged)

    # Additional UX-level requirement for Phase 4:
    # ownership notes should not be blank because this affects operational handoff.
    if not isinstance(merged.get("ownership_notes"), str) or not merged[
        "ownership_notes"
    ].strip():
        errors.append("'ownership_notes' cannot be empty")

    return len(errors) == 0, errors


def questionnaire_option_sets() -> Dict[str, List[str]]:
    """Expose select/radio options for UI controls."""
    return {
        "goal": sorted(GOALS),
        "source_of_truth": sorted(SOURCE_OF_TRUTH),
        "sync_direction": sorted(SYNC_DIRECTIONS),
        "trigger_mode": sorted(TRIGGER_MODES),
        "latency_slo": sorted(LATENCY_SLOS),
        "conflict_strategy": sorted(CONFLICT_STRATEGIES),
        "error_strategy": sorted(ERROR_STRATEGIES),
        "pii_handling": sorted(PII_HANDLING_MODES),
        "backoff": sorted(BACKOFF_STRATEGIES),
    }
