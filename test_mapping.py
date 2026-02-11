from contracts import validate_mapping_result
from mapper import generate_mappings
from prompts import create_mapping_prompt


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
                    "required": ["id"],
                    "properties": {
                        "id": {"type": "string"},
                        "email": {"type": "string", "format": "email"},
                    },
                }
            }
        },
    }


def test_create_mapping_prompt_contains_api_titles_and_schema_context():
    parsed_a = {
        "info": {"title": "Source API"},
        "schemas": {"User": {"email": {"type": "string", "required": True}}},
    }
    parsed_b = {
        "info": {"title": "Target API"},
        "schemas": {"Customer": {"email_address": {"type": "string", "required": True}}},
    }

    prompt = create_mapping_prompt(parsed_a, parsed_b)

    assert "Source API" in prompt
    assert "Target API" in prompt
    assert "entity_mappings" in prompt
    assert "warnings" in prompt


def test_generate_mappings_contract_valid_payload_from_mock_llm():
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
                            "notes": "Normalize before writing",
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

    result = generate_mappings(
        _sample_openapi("API A"),
        _sample_openapi("API B"),
        llm_client=MockLLMClient(llm_payload),
    )

    assert result["success"] is True
    is_valid, errors = validate_mapping_result(result["data"])
    assert is_valid is True
    assert errors == []