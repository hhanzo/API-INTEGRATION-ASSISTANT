"""Runtime mapping service for Phase 2.

This module converts OpenAPI specs into a mapping-friendly shape,
calls the LLM for entity/field mapping suggestions, and validates
the result against the canonical mapping contract.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from contracts import validate_mapping_result
from llm import GeminiClient
from prompts import create_mapping_prompt


def normalize_openapi_for_mapping(openapi_spec: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize OpenAPI-like payload into prompt-friendly schema summary."""
    info = openapi_spec.get("info", {}) if isinstance(openapi_spec, dict) else {}

    # If caller already provided parse_api_spec-like payload, pass-through schemas.
    if isinstance(openapi_spec, dict) and isinstance(openapi_spec.get("schemas"), dict):
        schemas = openapi_spec.get("schemas", {})
    else:
        raw_schemas = (
            openapi_spec.get("components", {}).get("schemas", {})
            if isinstance(openapi_spec, dict)
            else {}
        )
        schemas = {
            schema_name: _simplify_schema(schema_def)
            for schema_name, schema_def in raw_schemas.items()
            if isinstance(schema_def, dict)
        }

    title = info.get("title") if isinstance(info, dict) else None
    return {
        "info": {"title": title or "Unknown API"},
        "schemas": schemas,
    }


def generate_mappings(
    openapi_a: Dict[str, Any],
    openapi_b: Dict[str, Any],
    llm_client: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Generate mapping suggestions between two API specs.

    Returns:
        {
          "success": bool,
          "data": mapping_result_contract_shape,
          "error": Optional[str],
          "raw_response": Optional[str]
        }
    """
    parsed_a = normalize_openapi_for_mapping(openapi_a)
    parsed_b = normalize_openapi_for_mapping(openapi_b)
    prompt = create_mapping_prompt(parsed_a, parsed_b)

    client = llm_client or GeminiClient()
    result = client.analyze_apis(prompt)

    if result.get("error"):
        warning = f"LLM mapping generation failed: {result['error']}"
        return {
            "success": False,
            "data": _default_mapping_result([warning]),
            "error": result["error"],
            "raw_response": result.get("response"),
        }

    parsed = result.get("parsed")
    if not isinstance(parsed, dict):
        error = "LLM response did not produce valid JSON mapping payload"
        return {
            "success": False,
            "data": _default_mapping_result([error]),
            "error": error,
            "raw_response": result.get("response"),
        }

    normalized = _normalize_mapping_result(parsed)
    is_valid, errors = validate_mapping_result(normalized)
    if not is_valid:
        return {
            "success": False,
            "data": _default_mapping_result(
                ["Mapping payload failed contract validation", *errors]
            ),
            "error": "Invalid mapping payload",
            "raw_response": result.get("response"),
        }

    return {
        "success": True,
        "data": normalized,
        "error": None,
        "raw_response": result.get("response"),
    }


def _normalize_mapping_result(data: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure optional mapping keys exist with safe defaults."""
    normalized = dict(data)
    normalized.setdefault("entity_mappings", [])
    normalized.setdefault("unmapped_entities_a", [])
    normalized.setdefault("unmapped_entities_b", [])
    normalized.setdefault("warnings", [])
    return normalized


def _default_mapping_result(warnings: Optional[list[str]] = None) -> Dict[str, Any]:
    """Return empty mapping payload that still satisfies mapping contract."""
    return {
        "entity_mappings": [],
        "unmapped_entities_a": [],
        "unmapped_entities_b": [],
        "warnings": warnings or [],
    }


def _simplify_schema(schema: Dict[str, Any]) -> Dict[str, Any]:
    """Simplify OpenAPI schema to property-level mapping hints."""
    properties = schema.get("properties", {}) if isinstance(schema, dict) else {}
    required_fields = schema.get("required", []) if isinstance(schema, dict) else []

    simplified: Dict[str, Any] = {}
    for prop_name, prop_def in properties.items():
        if not isinstance(prop_def, dict):
            continue
        simplified[prop_name] = {
            "type": prop_def.get("type", "unknown"),
            "format": prop_def.get("format"),
            "description": prop_def.get("description"),
            "required": prop_name in required_fields,
            "enum": prop_def.get("enum"),
        }

    return simplified
