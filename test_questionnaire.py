from questionnaire import (
    get_questionnaire_defaults,
    merge_with_defaults,
    questionnaire_option_sets,
    validate_questionnaire_answers,
)


def test_get_questionnaire_defaults_has_required_keys():
    defaults = get_questionnaire_defaults()

    assert defaults["goal"] == "sync"
    assert defaults["retry_policy"]["max_retries"] == 3
    assert "ownership_notes" in defaults


def test_merge_with_defaults_handles_partial_payload():
    merged = merge_with_defaults(
        {
            "goal": "migrate",
            "retry_policy": {"max_retries": 5},
        }
    )

    assert merged["goal"] == "migrate"
    assert merged["retry_policy"]["max_retries"] == 5
    # preserved from defaults
    assert merged["retry_policy"]["backoff"] == "exponential"


def test_validate_questionnaire_answers_valid_payload():
    answers = {
        "goal": "sync",
        "source_of_truth": "api_a",
        "sync_direction": "a_to_b",
        "trigger_mode": "event",
        "latency_slo": "near_realtime",
        "conflict_strategy": "source_priority",
        "error_strategy": "retry_then_dlq",
        "retry_policy": {"max_retries": 3, "backoff": "linear"},
        "idempotency": True,
        "pii_handling": "mask",
        "ownership_notes": "Platform team owns operations",
    }

    is_valid, errors = validate_questionnaire_answers(answers)
    assert is_valid is True
    assert errors == []


def test_validate_questionnaire_answers_requires_ownership_notes():
    answers = {
        "goal": "sync",
        "source_of_truth": "api_a",
        "sync_direction": "a_to_b",
        "trigger_mode": "event",
        "latency_slo": "near_realtime",
        "conflict_strategy": "source_priority",
        "error_strategy": "retry_then_dlq",
        "retry_policy": {"max_retries": 3, "backoff": "fixed"},
        "idempotency": True,
        "pii_handling": "mask",
        "ownership_notes": "   ",
    }

    is_valid, errors = validate_questionnaire_answers(answers)
    assert is_valid is False
    assert any("ownership_notes" in err for err in errors)


def test_questionnaire_option_sets_exposes_enums():
    options = questionnaire_option_sets()

    assert "goal" in options
    assert "sync" in options["goal"]
    assert "backoff" in options
    assert "exponential" in options["backoff"]
