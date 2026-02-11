from contracts import validate_integration_answers, validate_integration_plan, validate_mapping_result
from mapper import generate_mappings
from plan_generator import generate_integration_plan
from questionnaire import validate_questionnaire_answers


class MockLLMClient:
    def __init__(self, result):
        self._result = result

    def analyze_apis(self, prompt: str):
        return self._result


def _sample_openapi(title: str):
    return {
        "info": {"title": title, "version": "1.0.0"},
        "paths": {},
        "components": {
            "schemas": {
                "User": {
                    "type": "object",
                    "required": ["id", "email"],
                    "properties": {
                        "id": {"type": "string"},
                        "email": {"type": "string", "format": "email"},
                    },
                }
            }
        },
    }


def _sample_answers():
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
        "ownership_notes": "Platform integrations squad",
    }


def test_end_to_end_mapping_questionnaire_plan_happy_path():
    llm_payload = {
        "response": "{}",
        "parsed": {
            "entity_mappings": [
                {
                    "api_a_entity": "User",
                    "api_b_entity": "Customer",
                    "confidence": "HIGH",
                    "reasoning": "Equivalent entities",
                    "field_mappings": [
                        {
                            "api_a_field": "email",
                            "api_b_field": "email_address",
                            "confidence": "MEDIUM",
                            "transformation": "lowercase",
                            "notes": "normalize",
                        }
                    ],
                }
            ],
            "unmapped_entities_a": [],
            "unmapped_entities_b": [],
            "warnings": [],
        },
        "error": None,
    }

    openapi_a = _sample_openapi("Source API")
    openapi_b = _sample_openapi("Target API")

    mapping_outcome = generate_mappings(
        openapi_a,
        openapi_b,
        llm_client=MockLLMClient(llm_payload),
    )
    assert mapping_outcome["success"] is True

    map_valid, map_errors = validate_mapping_result(mapping_outcome["data"])
    assert map_valid is True
    assert map_errors == []

    answers = _sample_answers()
    answers_valid, answers_errors = validate_questionnaire_answers(answers)
    assert answers_valid is True
    assert answers_errors == []

    contract_answers_valid, contract_answers_errors = validate_integration_answers(answers)
    assert contract_answers_valid is True
    assert contract_answers_errors == []

    plan_outcome = generate_integration_plan(
        openapi_a=openapi_a,
        openapi_b=openapi_b,
        mapping_result=mapping_outcome["data"],
        integration_answers=answers,
    )

    assert plan_outcome["success"] is True
    plan_valid, plan_errors = validate_integration_plan(plan_outcome["data"])
    assert plan_valid is True
    assert plan_errors == []
    assert len(plan_outcome["data"]["flows"]) >= 1
