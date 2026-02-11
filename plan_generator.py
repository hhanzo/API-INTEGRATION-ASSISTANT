"""Deterministic integration plan generator for Phase 5."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from contracts import validate_integration_plan


def generate_integration_plan(
    openapi_a: Dict[str, Any],
    openapi_b: Dict[str, Any],
    mapping_result: Dict[str, Any],
    integration_answers: Dict[str, Any],
) -> Dict[str, Any]:
    """Build a contract-compliant integration plan from upstream artifacts."""
    api_a_title = _api_title(openapi_a, "API A")
    api_b_title = _api_title(openapi_b, "API B")

    flows = _build_flows(mapping_result, integration_answers)
    risks = _build_risks(mapping_result)
    open_questions = _build_open_questions(mapping_result)

    plan = {
        "summary": {
            "name": f"{api_a_title} ↔ {api_b_title} Integration Plan",
            "goal": integration_answers.get("goal", "sync"),
            "direction": integration_answers.get("sync_direction", "a_to_b"),
            "source_of_truth": integration_answers.get("source_of_truth", "api_a"),
            "entities_mapped": len(mapping_result.get("entity_mappings", [])),
        },
        "flows": flows,
        "open_questions": open_questions,
        "risks": risks,
        "implementation_backlog": _build_backlog(integration_answers),
    }

    is_valid, errors = validate_integration_plan(plan)
    return {
        "success": is_valid,
        "data": plan if is_valid else _fallback_plan(errors),
        "error": None if is_valid else "Generated plan failed validation",
        "validation_errors": [] if is_valid else errors,
    }


def render_integration_plan_markdown(plan: Dict[str, Any]) -> str:
    """Render integration plan JSON into a readable Markdown summary."""
    summary = plan.get("summary", {})
    lines = [
        f"# {summary.get('name', 'Integration Plan')}",
        "",
        "## Summary",
        f"- Goal: `{summary.get('goal', 'sync')}`",
        f"- Direction: `{summary.get('direction', 'a_to_b')}`",
        f"- Source of truth: `{summary.get('source_of_truth', 'api_a')}`",
        f"- Entities mapped: `{summary.get('entities_mapped', 0)}`",
        "",
        "## Flows",
    ]

    for flow in plan.get("flows", []):
        lines.extend(
            [
                f"### {flow.get('name', 'Unnamed flow')}",
                f"- Direction: `{flow.get('direction', '')}`",
                f"- Trigger: `{flow.get('trigger', '')}`",
                "- Steps:",
            ]
        )
        for step in flow.get("steps", []):
            lines.append(f"  - {step}")

        lines.append("- Field mappings:")
        for field_map in flow.get("field_map", []):
            lines.append(f"  - {field_map}")

        lines.append("")

    lines.extend(["## Risks"])
    for risk in plan.get("risks", []):
        lines.append(f"- {risk}")

    lines.extend(["", "## Open Questions"])
    for question in plan.get("open_questions", []):
        lines.append(f"- {question}")

    lines.extend(["", "## Implementation Backlog"])
    for item in plan.get("implementation_backlog", []):
        lines.append(f"- {item}")

    return "\n".join(lines).strip() + "\n"


def _build_flows(mapping_result: Dict[str, Any], answers: Dict[str, Any]) -> List[Dict[str, Any]]:
    entity_mappings = mapping_result.get("entity_mappings", [])
    direction = _human_direction(answers.get("sync_direction", "a_to_b"))
    trigger = answers.get("trigger_mode", "event")

    flows = []
    for mapping in entity_mappings:
        a_entity = mapping.get("api_a_entity", "SourceEntity")
        b_entity = mapping.get("api_b_entity", "TargetEntity")

        field_map_lines = []
        for field in mapping.get("field_mappings", []):
            a_field = field.get("api_a_field", "")
            b_field = field.get("api_b_field", "")
            confidence = field.get("confidence", "")
            transformation = field.get("transformation")
            transform_text = (
                f" | transform: {transformation}"
                if transformation not in (None, "", {})
                else ""
            )
            field_map_lines.append(f"{a_field} -> {b_field} ({confidence}){transform_text}")

        flows.append(
            {
                "name": f"Sync {a_entity} to {b_entity}",
                "direction": direction,
                "trigger": trigger,
                "steps": [
                    f"Capture {a_entity} change event",
                    "Apply field transformations",
                    f"Upsert {b_entity} in destination API",
                    "Record outcome and retry on transient failures",
                ],
                "field_map": field_map_lines,
                "error_handling": {
                    "strategy": answers.get("error_strategy", "retry_then_dlq"),
                    "retry_policy": answers.get(
                        "retry_policy", {"max_retries": 3, "backoff": "exponential"}
                    ),
                },
                "auth": {
                    "source_of_truth": answers.get("source_of_truth", "api_a"),
                    "idempotency_required": bool(answers.get("idempotency", True)),
                },
                "observability": {
                    "metrics": [
                        "sync_success_rate",
                        "sync_error_rate",
                        "retry_count",
                        "latency_p95",
                    ],
                    "owner": answers.get("ownership_notes", ""),
                },
            }
        )

    if flows:
        return flows

    return [
        {
            "name": "Initial generic synchronization flow",
            "direction": direction,
            "trigger": trigger,
            "steps": [
                "Identify source events",
                "Transform payload to destination schema",
                "Call destination API",
                "Handle retry and observability hooks",
            ],
            "field_map": [],
            "error_handling": {
                "strategy": answers.get("error_strategy", "retry_then_dlq"),
                "retry_policy": answers.get(
                    "retry_policy", {"max_retries": 3, "backoff": "exponential"}
                ),
            },
            "auth": {
                "source_of_truth": answers.get("source_of_truth", "api_a"),
                "idempotency_required": bool(answers.get("idempotency", True)),
            },
            "observability": {
                "metrics": ["sync_success_rate", "sync_error_rate", "latency_p95"],
                "owner": answers.get("ownership_notes", ""),
            },
        }
    ]


def _build_open_questions(mapping_result: Dict[str, Any]) -> List[str]:
    questions = []
    for entity in mapping_result.get("unmapped_entities_a", []):
        questions.append(f"How should API A entity '{entity}' be represented in API B?")
    for entity in mapping_result.get("unmapped_entities_b", []):
        questions.append(f"Should API B entity '{entity}' be sourced, ignored, or reverse-synced?")
    return questions


def _build_risks(mapping_result: Dict[str, Any]) -> List[str]:
    risks = list(mapping_result.get("warnings", []))
    for entity_map in mapping_result.get("entity_mappings", []):
        if entity_map.get("confidence") == "LOW":
            risks.append(
                f"Low confidence entity mapping: {entity_map.get('api_a_entity')} -> {entity_map.get('api_b_entity')}"
            )
        for field_map in entity_map.get("field_mappings", []):
            if field_map.get("confidence") == "LOW":
                risks.append(
                    f"Low confidence field mapping: {field_map.get('api_a_field')} -> {field_map.get('api_b_field')}"
                )

    if not risks:
        risks.append("No explicit risks detected from mapping stage")
    return risks


def _build_backlog(answers: Dict[str, Any]) -> List[str]:
    return [
        "Implement source connector authentication and token refresh",
        "Implement destination connector upsert operations",
        "Build transformation layer for mapped fields",
        "Implement retry/dead-letter behavior",
        f"Configure monitoring ownership: {answers.get('ownership_notes', 'TBD')}",
    ]


def _fallback_plan(errors: List[str]) -> Dict[str, Any]:
    return {
        "summary": {"name": "Integration Plan (Fallback)"},
        "flows": [
            {
                "name": "Fallback flow",
                "direction": "A->B",
                "trigger": "manual",
                "steps": ["Review validation errors", "Fix upstream artifacts"],
                "field_map": [],
                "error_handling": {"strategy": "halt_pipeline", "validation_errors": errors},
                "auth": {},
                "observability": {"metrics": ["validation_error_count"]},
            }
        ],
        "open_questions": ["Resolve integration plan validation errors before rollout"],
        "risks": ["Plan generation produced invalid structure"],
        "implementation_backlog": ["Correct upstream mapping/answers payload"],
    }


def _api_title(spec: Dict[str, Any], fallback: str) -> str:
    return spec.get("info", {}).get("title", fallback)


def _human_direction(sync_direction: str) -> str:
    mapping = {
        "a_to_b": "A->B",
        "b_to_a": "B->A",
        "bidirectional": "A<->B",
    }
    return mapping.get(sync_direction, "A->B")
