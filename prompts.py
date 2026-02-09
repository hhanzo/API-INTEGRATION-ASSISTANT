import json

def create_mapping_prompt(parsed_a: dict, parsed_b: dict) -> str:
    """
    Create prompt for Claude to identify entity and field mappings.
    """
    
    # Prepare simplified view of schemas
    schemas_a = _format_schemas(parsed_a['schemas'], parsed_a['info']['title'])
    schemas_b = _format_schemas(parsed_b['schemas'], parsed_b['info']['title'])
    
    prompt = f"""You are an API integration expert. Analyze these two API specifications and identify how to map data between them.

API A: {parsed_a['info']['title']}
{schemas_a}

API B: {parsed_b['info']['title']}
{schemas_b}

Your task:
1. Identify common entities (e.g., if API A has "User" and API B has "Customer", they might represent the same thing)
2. For each matched entity, map fields between the two APIs
3. Rate the confidence of each mapping (HIGH, MEDIUM, LOW)
4. Note any data type mismatches or transformations needed

Respond in this EXACT JSON format:
{{
  "entity_mappings": [
    {{
      "api_a_entity": "User",
      "api_b_entity": "Customer",
      "confidence": "HIGH",
      "reasoning": "Both represent user accounts",
      "field_mappings": [
        {{
          "api_a_field": "user_id",
          "api_b_field": "customer_id",
          "confidence": "HIGH",
          "transformation": null,
          "notes": "Direct mapping"
        }},
        {{
          "api_a_field": "created_timestamp",
          "api_b_field": "created_at",
          "confidence": "MEDIUM",
          "transformation": "Convert Unix timestamp to ISO 8601",
          "notes": "Date format mismatch"
        }}
      ]
    }}
  ],
  "unmapped_entities_a": ["Order", "Payment"],
  "unmapped_entities_b": ["Invoice"]
}}

Return ONLY valid JSON, no other text."""
    
    return prompt

def _format_schemas(schemas: dict, api_name: str) -> str:
    """Format schemas for the prompt."""
    if not schemas:
        return f"{api_name} has no schemas defined."
    
    output = f"\n{api_name} Schemas:\n"
    for schema_name, fields in schemas.items():
        output += f"\n  {schema_name}:\n"
        for field_name, field_info in fields.items():
            required = "required" if field_info.get('required') else "optional"
            output += f"    - {field_name}: {field_info['type']} ({required})\n"
            if field_info.get('description'):
                output += f"        Description: {field_info['description']}\n"
    
    return output