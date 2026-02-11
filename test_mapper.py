from mapper import generate_mappings, normalize_openapi_for_mapping


class MockLLMClient:
    def __init__(self, result):
        self._result = result

    def analyze_apis(self, prompt: str):
        return self._result


def test_normalize_openapi_for_mapping_from_components_schemas():
    openapi = {
        "info": {"title": "Billing API"},
        "components": {
            "schemas": {
                "Customer": {
                    "type": "object",
                    "required": ["id"],
                    "properties": {
                        "id": {"type": "string", "description": "Customer id"},
                        "email": {"type": "string", "format": "email"},
                    },
                }
            }
        },
    }

    normalized = normalize_openapi_for_mapping(openapi)

    assert normalized["info"]["title"] == "Billing API"
    assert "Customer" in normalized["schemas"]
    assert normalized["schemas"]["Customer"]["id"]["required"] is True
    assert normalized["schemas"]["Customer"]["email"]["format"] == "email"


def test_normalize_openapi_for_mapping_passthrough_schemas_shape():
    parsed_like = {
        "info": {"title": "Parsed API"},
        "schemas": {
            "User": {
                "id": {"type": "string", "required": True},
            }
        },
    }

    normalized = normalize_openapi_for_mapping(parsed_like)
    assert normalized["schemas"] == parsed_like["schemas"]


def test_generate_mappings_success_valid_payload():
    llm_payload = {
        "response": "{}",
        "parsed": {
            "entity_mappings": [
                {
                    "api_a_entity": "User",
                    "api_b_entity": "Customer",
                    "confidence": "HIGH",
                    "reasoning": "Same concept",
                    "field_mappings": [
                        {
                            "api_a_field": "email",
                            "api_b_field": "email_address",
                            "confidence": "MEDIUM",
                            "transformation": "lowercase",
                            "notes": "Normalize format",
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
        {"info": {"title": "A"}, "components": {"schemas": {}}},
        {"info": {"title": "B"}, "components": {"schemas": {}}},
        llm_client=MockLLMClient(llm_payload),
    )

    assert result["success"] is True
    assert result["error"] is None
    assert result["data"]["entity_mappings"][0]["api_a_entity"] == "User"


def test_generate_mappings_llm_error_returns_default_contract_shape():
    llm_payload = {
        "response": None,
        "parsed": None,
        "error": "quota exceeded",
    }

    result = generate_mappings(
        {"info": {"title": "A"}, "components": {"schemas": {}}},
        {"info": {"title": "B"}, "components": {"schemas": {}}},
        llm_client=MockLLMClient(llm_payload),
    )

    assert result["success"] is False
    assert result["error"] == "quota exceeded"
    assert result["data"]["entity_mappings"] == []
    assert result["data"]["unmapped_entities_a"] == []
    assert result["data"]["unmapped_entities_b"] == []
    assert result["data"]["warnings"]


def test_generate_mappings_non_dict_parsed_payload_fails_safely():
    llm_payload = {
        "response": "not json",
        "parsed": None,
        "error": None,
    }

    result = generate_mappings(
        {"info": {"title": "A"}, "components": {"schemas": {}}},
        {"info": {"title": "B"}, "components": {"schemas": {}}},
        llm_client=MockLLMClient(llm_payload),
    )

    assert result["success"] is False
    assert "did not produce valid JSON" in result["error"]
    assert result["data"]["entity_mappings"] == []


def test_generate_mappings_invalid_contract_payload_fails_safely():
    llm_payload = {
        "response": "{}",
        "parsed": {
            "entity_mappings": [
                {
                    "api_a_entity": "User",
                    "api_b_entity": "Customer",
                    "confidence": "NOT_VALID",
                    "field_mappings": [],
                }
            ],
            "unmapped_entities_a": [],
            "unmapped_entities_b": [],
        },
        "error": None,
    }

    result = generate_mappings(
        {"info": {"title": "A"}, "components": {"schemas": {}}},
        {"info": {"title": "B"}, "components": {"schemas": {}}},
        llm_client=MockLLMClient(llm_payload),
    )

    assert result["success"] is False
    assert result["error"] == "Invalid mapping payload"
    assert "failed contract validation" in " ".join(result["data"]["warnings"]).lower()
