from contracts import (
    validate_contract,
    validate_extracted_api,
    validate_integration_answers,
    validate_integration_plan,
    validate_mapping_result,
)


def test_validate_extracted_api_valid_payload():
    payload = {
        "api_id": "api_a",
        "source_url": "https://example.com/docs",
        "openapi": {"openapi": "3.1.0", "paths": {}},
        "normalized": {
            "entities": [
                {
                    "name": "Customer",
                    "fields": [
                        {"name": "id", "type": "string", "required": True},
                        {"name": "email", "type": "string", "required": False},
                    ],
                }
            ],
            "operations": [{"method": "GET", "path": "/customers"}],
            "auth": {"type": "bearer"},
        },
    }

    is_valid, errors = validate_extracted_api(payload)

    assert is_valid is True
    assert errors == []


def test_validate_extracted_api_invalid_payload():
    payload = {
        "api_id": "invalid",
        "source_url": "",
        "openapi": "not-object",
        "normalized": {"entities": "nope", "operations": []},
    }

    is_valid, errors = validate_extracted_api(payload)

    assert is_valid is False
    assert len(errors) >= 3


def test_validate_mapping_result_valid_payload():
    payload = {
        "entity_mappings": [
            {
                "api_a_entity": "User",
                "api_b_entity": "Customer",
                "confidence": "HIGH",
                "reasoning": "Same semantic entity",
                "field_mappings": [
                    {
                        "api_a_field": "email",
                        "api_b_field": "email_address",
                        "confidence": "MEDIUM",
                        "transformation": "lowercase",
                        "notes": "Normalize casing",
                    }
                ],
            }
        ],
        "unmapped_entities_a": [],
        "unmapped_entities_b": ["Invoice"],
        "warnings": [],
    }

    is_valid, errors = validate_mapping_result(payload)

    assert is_valid is True
    assert errors == []


def test_validate_mapping_result_rejects_bad_confidence():
    payload = {
        "entity_mappings": [
            {
                "api_a_entity": "User",
                "api_b_entity": "Customer",
                "confidence": "UNKNOWN",
                "field_mappings": [
                    {
                        "api_a_field": "id",
                        "api_b_field": "id",
                        "confidence": "HIGH",
                        "transformation": None,
                    }
                ],
            }
        ],
        "unmapped_entities_a": [],
        "unmapped_entities_b": [],
    }

    is_valid, errors = validate_mapping_result(payload)

    assert is_valid is False
    assert any("confidence" in err for err in errors)


def test_validate_integration_answers_valid_payload():
    payload = {
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
        "ownership_notes": "Integration owned by platform team",
    }

    is_valid, errors = validate_integration_answers(payload)

    assert is_valid is True
    assert errors == []


def test_validate_integration_answers_invalid_retry_policy():
    payload = {
        "goal": "sync",
        "source_of_truth": "api_a",
        "sync_direction": "a_to_b",
        "trigger_mode": "event",
        "latency_slo": "near_realtime",
        "conflict_strategy": "source_priority",
        "error_strategy": "retry_then_dlq",
        "retry_policy": {"max_retries": -1, "backoff": "curve"},
        "idempotency": True,
        "pii_handling": "mask",
        "ownership_notes": "Owned",
    }

    is_valid, errors = validate_integration_answers(payload)

    assert is_valid is False
    assert any("retry_policy.max_retries" in err for err in errors)
    assert any("retry_policy.backoff" in err for err in errors)


def test_validate_integration_plan_valid_payload():
    payload = {
        "summary": {"name": "Customer sync"},
        "flows": [
            {
                "name": "Sync customer",
                "direction": "A->B",
                "trigger": "event",
                "steps": ["Receive event", "Transform payload", "Call destination API"],
                "field_map": ["email -> email_address"],
                "error_handling": {"strategy": "retry_then_dlq"},
                "auth": {"type": "bearer"},
                "observability": {"metrics": ["success_rate"]},
            }
        ],
        "open_questions": [],
        "risks": ["Rate limit mismatch"],
        "implementation_backlog": ["Implement worker"],
    }

    is_valid, errors = validate_integration_plan(payload)

    assert is_valid is True
    assert errors == []


def test_validate_contract_dispatch_and_unknown():
    valid_mapping = {
        "entity_mappings": [],
        "unmapped_entities_a": [],
        "unmapped_entities_b": [],
    }

    is_valid, errors = validate_contract("mapping_result", valid_mapping)
    assert is_valid is True
    assert errors == []

    is_valid_unknown, errors_unknown = validate_contract("does_not_exist", {})
    assert is_valid_unknown is False
    assert errors_unknown == ["Unknown contract: does_not_exist"]
