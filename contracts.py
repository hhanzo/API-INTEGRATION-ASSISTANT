"""
Canonical pipeline contracts for the integration assistant.

Phase 1 introduces these validation helpers so all future stages can rely
on consistent artifact shapes.
"""

from __future__ import annotations

from typing import Any, Dict, List, Tuple


CONFIDENCE_LEVELS = {"HIGH", "MEDIUM", "LOW"}

GOALS = {"sync", "enrich", "migrate", "bidirectional"}
SOURCE_OF_TRUTH = {"api_a", "api_b", "per_entity"}
SYNC_DIRECTIONS = {"a_to_b", "b_to_a", "bidirectional"}
TRIGGER_MODES = {"event", "polling", "manual", "batch"}
LATENCY_SLOS = {"realtime", "near_realtime", "hourly", "daily"}
CONFLICT_STRATEGIES = {"last_write_wins", "source_priority", "manual_review"}
ERROR_STRATEGIES = {"retry_then_dlq", "skip_and_log", "halt_pipeline"}
PII_HANDLING_MODES = {"none", "mask", "encrypt"}
BACKOFF_STRATEGIES = {"exponential", "linear", "fixed"}


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _validate_enum(
    data: Dict[str, Any], key: str, allowed: set[str], errors: List[str]
) -> None:
    value = data.get(key)
    if value not in allowed:
        errors.append(f"'{key}' must be one of {sorted(allowed)}")


def _validate_list_of_strings(
    data: Dict[str, Any], key: str, errors: List[str], required: bool = False
) -> None:
    if key not in data:
        if required:
            errors.append(f"Missing required key: '{key}'")
        return

    value = data[key]
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        errors.append(f"'{key}' must be a list of strings")


def validate_extracted_api(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate extracted API artifact.

    Expected shape:
    {
      "api_id": "api_a|api_b",
      "source_url": "...",
      "openapi": {...},
      "normalized": {
        "entities": [...],
        "operations": [...],
        "auth": {...}
      }
    }
    """
    errors: List[str] = []

    if not isinstance(data, dict):
        return False, ["Extracted API payload must be an object"]

    if data.get("api_id") not in {"api_a", "api_b"}:
        errors.append("'api_id' must be either 'api_a' or 'api_b'")

    if not _is_non_empty_string(data.get("source_url")):
        errors.append("'source_url' must be a non-empty string")

    if not isinstance(data.get("openapi"), dict):
        errors.append("'openapi' must be an object")

    normalized = data.get("normalized")
    if not isinstance(normalized, dict):
        errors.append("'normalized' must be an object")
        return len(errors) == 0, errors

    entities = normalized.get("entities")
    if not isinstance(entities, list):
        errors.append("'normalized.entities' must be a list")
    else:
        for i, entity in enumerate(entities):
            if not isinstance(entity, dict):
                errors.append(f"'normalized.entities[{i}]' must be an object")
                continue

            if not _is_non_empty_string(entity.get("name")):
                errors.append(f"'normalized.entities[{i}].name' must be a non-empty string")

            fields = entity.get("fields")
            if not isinstance(fields, list):
                errors.append(f"'normalized.entities[{i}].fields' must be a list")
                continue

            for j, field in enumerate(fields):
                if not isinstance(field, dict):
                    errors.append(
                        f"'normalized.entities[{i}].fields[{j}]' must be an object"
                    )
                    continue
                if not _is_non_empty_string(field.get("name")):
                    errors.append(
                        f"'normalized.entities[{i}].fields[{j}].name' must be a non-empty string"
                    )
                if not _is_non_empty_string(field.get("type")):
                    errors.append(
                        f"'normalized.entities[{i}].fields[{j}].type' must be a non-empty string"
                    )
                if "required" in field and not isinstance(field.get("required"), bool):
                    errors.append(
                        f"'normalized.entities[{i}].fields[{j}].required' must be boolean"
                    )

    operations = normalized.get("operations")
    if not isinstance(operations, list):
        errors.append("'normalized.operations' must be a list")
    else:
        for i, operation in enumerate(operations):
            if not isinstance(operation, dict):
                errors.append(f"'normalized.operations[{i}]' must be an object")
                continue
            if not _is_non_empty_string(operation.get("method")):
                errors.append(
                    f"'normalized.operations[{i}].method' must be a non-empty string"
                )
            if not _is_non_empty_string(operation.get("path")):
                errors.append(
                    f"'normalized.operations[{i}].path' must be a non-empty string"
                )

    if "auth" in normalized and not isinstance(normalized.get("auth"), dict):
        errors.append("'normalized.auth' must be an object when present")

    return len(errors) == 0, errors


def validate_mapping_result(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate entity/field mapping artifact."""
    errors: List[str] = []

    if not isinstance(data, dict):
        return False, ["Mapping result payload must be an object"]

    entity_mappings = data.get("entity_mappings")
    if not isinstance(entity_mappings, list):
        errors.append("'entity_mappings' must be a list")
    else:
        for i, mapping in enumerate(entity_mappings):
            if not isinstance(mapping, dict):
                errors.append(f"'entity_mappings[{i}]' must be an object")
                continue

            if not _is_non_empty_string(mapping.get("api_a_entity")):
                errors.append(
                    f"'entity_mappings[{i}].api_a_entity' must be a non-empty string"
                )
            if not _is_non_empty_string(mapping.get("api_b_entity")):
                errors.append(
                    f"'entity_mappings[{i}].api_b_entity' must be a non-empty string"
                )
            if mapping.get("confidence") not in CONFIDENCE_LEVELS:
                errors.append(
                    f"'entity_mappings[{i}].confidence' must be one of {sorted(CONFIDENCE_LEVELS)}"
                )

            field_mappings = mapping.get("field_mappings")
            if not isinstance(field_mappings, list):
                errors.append(f"'entity_mappings[{i}].field_mappings' must be a list")
                continue

            for j, field_map in enumerate(field_mappings):
                if not isinstance(field_map, dict):
                    errors.append(
                        f"'entity_mappings[{i}].field_mappings[{j}]' must be an object"
                    )
                    continue
                if not _is_non_empty_string(field_map.get("api_a_field")):
                    errors.append(
                        f"'entity_mappings[{i}].field_mappings[{j}].api_a_field' must be a non-empty string"
                    )
                if not _is_non_empty_string(field_map.get("api_b_field")):
                    errors.append(
                        f"'entity_mappings[{i}].field_mappings[{j}].api_b_field' must be a non-empty string"
                    )
                if field_map.get("confidence") not in CONFIDENCE_LEVELS:
                    errors.append(
                        f"'entity_mappings[{i}].field_mappings[{j}].confidence' must be one of {sorted(CONFIDENCE_LEVELS)}"
                    )

                transformation = field_map.get("transformation")
                if transformation is not None and not isinstance(transformation, (str, dict)):
                    errors.append(
                        f"'entity_mappings[{i}].field_mappings[{j}].transformation' must be null, string, or object"
                    )

    _validate_list_of_strings(data, "unmapped_entities_a", errors, required=True)
    _validate_list_of_strings(data, "unmapped_entities_b", errors, required=True)
    _validate_list_of_strings(data, "warnings", errors, required=False)

    return len(errors) == 0, errors


def validate_integration_answers(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate questionnaire output artifact."""
    errors: List[str] = []

    if not isinstance(data, dict):
        return False, ["Integration answers payload must be an object"]

    _validate_enum(data, "goal", GOALS, errors)
    _validate_enum(data, "source_of_truth", SOURCE_OF_TRUTH, errors)
    _validate_enum(data, "sync_direction", SYNC_DIRECTIONS, errors)
    _validate_enum(data, "trigger_mode", TRIGGER_MODES, errors)
    _validate_enum(data, "latency_slo", LATENCY_SLOS, errors)
    _validate_enum(data, "conflict_strategy", CONFLICT_STRATEGIES, errors)
    _validate_enum(data, "error_strategy", ERROR_STRATEGIES, errors)
    _validate_enum(data, "pii_handling", PII_HANDLING_MODES, errors)

    retry_policy = data.get("retry_policy")
    if not isinstance(retry_policy, dict):
        errors.append("'retry_policy' must be an object")
    else:
        max_retries = retry_policy.get("max_retries")
        if not isinstance(max_retries, int) or max_retries < 0:
            errors.append("'retry_policy.max_retries' must be an integer >= 0")

        backoff = retry_policy.get("backoff")
        if backoff not in BACKOFF_STRATEGIES:
            errors.append(
                f"'retry_policy.backoff' must be one of {sorted(BACKOFF_STRATEGIES)}"
            )

    if not isinstance(data.get("idempotency"), bool):
        errors.append("'idempotency' must be boolean")

    if not isinstance(data.get("ownership_notes"), str):
        errors.append("'ownership_notes' must be a string")

    return len(errors) == 0, errors


def validate_integration_plan(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate final integration plan artifact."""
    errors: List[str] = []

    if not isinstance(data, dict):
        return False, ["Integration plan payload must be an object"]

    if not isinstance(data.get("summary"), dict):
        errors.append("'summary' must be an object")

    flows = data.get("flows")
    if not isinstance(flows, list):
        errors.append("'flows' must be a list")
    else:
        for i, flow in enumerate(flows):
            if not isinstance(flow, dict):
                errors.append(f"'flows[{i}]' must be an object")
                continue

            if not _is_non_empty_string(flow.get("name")):
                errors.append(f"'flows[{i}].name' must be a non-empty string")
            if not _is_non_empty_string(flow.get("direction")):
                errors.append(f"'flows[{i}].direction' must be a non-empty string")
            if not _is_non_empty_string(flow.get("trigger")):
                errors.append(f"'flows[{i}].trigger' must be a non-empty string")

            for key in ["steps", "field_map"]:
                if not isinstance(flow.get(key), list):
                    errors.append(f"'flows[{i}].{key}' must be a list")

            for key in ["error_handling", "auth", "observability"]:
                if not isinstance(flow.get(key), dict):
                    errors.append(f"'flows[{i}].{key}' must be an object")

    _validate_list_of_strings(data, "open_questions", errors, required=True)
    _validate_list_of_strings(data, "risks", errors, required=True)
    _validate_list_of_strings(data, "implementation_backlog", errors, required=True)

    return len(errors) == 0, errors


def validate_contract(contract_name: str, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Dispatch validator by contract name."""
    validators = {
        "extracted_api": validate_extracted_api,
        "mapping_result": validate_mapping_result,
        "integration_answers": validate_integration_answers,
        "integration_plan": validate_integration_plan,
    }

    validator = validators.get(contract_name)
    if not validator:
        return False, [f"Unknown contract: {contract_name}"]

    return validator(data)
