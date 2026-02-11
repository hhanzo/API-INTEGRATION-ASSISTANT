from plan_generator import generate_integration_plan, render_integration_plan_markdown


def _sample_openapi(title: str):
    return {
        "info": {"title": title, "version": "1.0.0"},
        "paths": {},
        "components": {"schemas": {}},
    }


def _sample_mapping_result():
    return {
        "entity_mappings": [
            {
                "api_a_entity": "User",
                "api_b_entity": "Customer",
                "confidence": "HIGH",
                "reasoning": "Equivalent business object",
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
        "unmapped_entities_a": ["Invoice"],
        "unmapped_entities_b": [],
        "warnings": ["Check type compatibility for created_at"],
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
        "ownership_notes": "Platform team",
    }


def test_generate_integration_plan_success():
    result = generate_integration_plan(
        openapi_a=_sample_openapi("CRM API"),
        openapi_b=_sample_openapi("Billing API"),
        mapping_result=_sample_mapping_result(),
        integration_answers=_sample_answers(),
    )

    assert result["success"] is True
    assert result["error"] is None
    plan = result["data"]

    assert "summary" in plan
    assert "flows" in plan
    assert len(plan["flows"]) >= 1
    assert "CRM API" in plan["summary"]["name"]
    assert "Billing API" in plan["summary"]["name"]


def test_generate_integration_plan_produces_open_questions_from_unmapped_entities():
    result = generate_integration_plan(
        openapi_a=_sample_openapi("A"),
        openapi_b=_sample_openapi("B"),
        mapping_result=_sample_mapping_result(),
        integration_answers=_sample_answers(),
    )

    plan = result["data"]
    assert any("Invoice" in question for question in plan["open_questions"])


def test_generate_integration_plan_uses_generic_flow_when_no_entity_mappings():
    empty_mapping = {
        "entity_mappings": [],
        "unmapped_entities_a": [],
        "unmapped_entities_b": [],
        "warnings": [],
    }

    result = generate_integration_plan(
        openapi_a=_sample_openapi("A"),
        openapi_b=_sample_openapi("B"),
        mapping_result=empty_mapping,
        integration_answers=_sample_answers(),
    )

    assert result["success"] is True
    plan = result["data"]
    assert plan["flows"][0]["name"] == "Initial generic synchronization flow"


def test_render_integration_plan_markdown_contains_sections():
    result = generate_integration_plan(
        openapi_a=_sample_openapi("CRM API"),
        openapi_b=_sample_openapi("Billing API"),
        mapping_result=_sample_mapping_result(),
        integration_answers=_sample_answers(),
    )

    markdown = render_integration_plan_markdown(result["data"])

    assert markdown.startswith("# ")
    assert "## Summary" in markdown
    assert "## Flows" in markdown
    assert "## Risks" in markdown
    assert "## Open Questions" in markdown
    assert "## Implementation Backlog" in markdown
