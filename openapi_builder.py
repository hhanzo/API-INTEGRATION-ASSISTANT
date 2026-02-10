"""
OpenAPI 3.1.0 Specification Builder
Converts extracted API data to valid OpenAPI 3.1.0 format
"""

import json
from typing import Dict, List, Any
from datetime import datetime

def build_openapi_spec(extracted_data: Dict) -> Dict:
    """
    Build a complete OpenAPI 3.1.0 specification from extracted data.
    
    Args:
        extracted_data: Data from APIExtractor
        
    Returns:
        Valid OpenAPI 3.1.0 specification
    """
    
    api_info = extracted_data.get('api_info', {})
    endpoints = extracted_data.get('endpoints', [])
    components = extracted_data.get('components', {})
    
    # Build OpenAPI structure
    openapi_spec = {
        "openapi": "3.1.0",
        "info": {
            "title": api_info.get('name', 'Extracted API'),
            "version": api_info.get('version', '1.0.0'),
            "description": api_info.get('description', 'API extracted from documentation'),
            "x-extracted-date": datetime.now().isoformat(),
            "x-source-url": api_info.get('source_url', '')
        },
        "servers": _build_servers(api_info),
        "paths": _build_paths(endpoints),
        "components": _build_components(components, endpoints),
        "tags": _extract_tags(endpoints)
    }
    
    # Add security if present
    if components.get('securitySchemes'):
        openapi_spec['security'] = _build_global_security(components['securitySchemes'])
    
    return openapi_spec

def _build_servers(api_info: Dict) -> List[Dict]:
    """Build servers array."""
    base_url = api_info.get('base_url', '')
    
    if not base_url:
        return [{"url": "https://api.example.com", "description": "API server (update this URL)"}]
    
    return [
        {
            "url": base_url,
            "description": "Production server"
        }
    ]

def _build_paths(endpoints: List[Dict]) -> Dict:
    """Build paths object from endpoints."""
    paths = {}
    
    for endpoint in endpoints:
        #path = endpoint.get('path', '/')
        raw_path = endpoint.get('path')
        path = raw_path if isinstance(raw_path, str) and raw_path.strip() else '/'

        method = endpoint.get('method', 'GET').lower()
        
        # Initialize path if not exists
        if path not in paths:
            paths[path] = {}
        

        safe_path = path.strip('/').replace('/', '_').replace('{', '').replace('}', '')
        operation_id = endpoint.get('operation_id')

        if not isinstance(operation_id, str) or not operation_id.strip():
            operation_id = f"{method}_{safe_path or 'root'}"

        # Build operation object
        operation = {
            "summary": endpoint.get('summary', ''),
            "description": endpoint.get('description', ''),
            "operationId": operation_id,
            "tags": endpoint.get('tags', []),
            "parameters": _build_parameters(endpoint.get('parameters', [])),
            "responses": _build_responses(endpoint.get('responses', {}))
        }
        
        # Add request body if present
        if endpoint.get('request_body'):
            operation['requestBody'] = _build_request_body(endpoint['request_body'])
        
        # Add security if present
        if endpoint.get('security'):
            operation['security'] = endpoint['security']
        
        # Add code samples if present
        if endpoint.get('x-code-samples'):
            operation['x-code-samples'] = endpoint['x-code-samples']
        
        paths[path][method] = operation
    
    return paths

def _build_parameters(parameters: List[Dict]) -> List[Dict]:
    """Build parameters array."""
    built_params = []
    
    for param in parameters:
        built_param = {
            "name": param.get('name', 'unknown'),
            "in": param.get('in', 'query'),
            "description": param.get('description', ''),
            "required": param.get('required', False),
            "schema": _build_schema(param.get('schema', {'type': 'string'}))
        }
        
        if 'example' in param:
            built_param['example'] = param['example']
        
        if 'examples' in param:
            built_param['examples'] = param['examples']
        
        built_params.append(built_param)
    
    return built_params

def _build_request_body(request_body: Dict) -> Dict:
    """Build request body object."""
    
    if not request_body:
        return {}
    
    built_body = {
        "description": request_body.get('description', ''),
        "required": request_body.get('required', False),
        "content": {}
    }
    
    # Handle content
    content = request_body.get('content', {})
    
    if not content:
        # Fallback: assume application/json
        content = {
            "application/json": {
                "schema": {"type": "object"}
            }
        }
    
    for media_type, media_data in content.items():
        built_body['content'][media_type] = {
            "schema": _build_schema(media_data.get('schema', {'type': 'object'}))
        }
        
        if 'example' in media_data:
            built_body['content'][media_type]['example'] = media_data['example']
        
        if 'examples' in media_data:
            built_body['content'][media_type]['examples'] = media_data['examples']
    
    return built_body

def _build_responses(responses: Dict) -> Dict:
    """Build responses object."""
    
    if not responses:
        # Default response
        return {
            "200": {
                "description": "Successful response",
                "content": {
                    "application/json": {
                        "schema": {"type": "object"}
                    }
                }
            }
        }
    
    built_responses = {}
    
    for status_code, response_data in responses.items():
        built_response = {
            "description": response_data.get('description', f"Response for status {status_code}")
        }
        
        # Add headers if present
        if 'headers' in response_data:
            built_response['headers'] = {}
            for header_name, header_data in response_data['headers'].items():
                built_response['headers'][header_name] = {
                    "description": header_data.get('description', ''),
                    "schema": _build_schema(header_data.get('schema', {'type': 'string'}))
                }
        
        # Add content if present
        if 'content' in response_data:
            built_response['content'] = {}
            for media_type, media_data in response_data['content'].items():
                built_response['content'][media_type] = {
                    "schema": _build_schema(media_data.get('schema', {'type': 'object'}))
                }
                
                if 'example' in media_data:
                    built_response['content'][media_type]['example'] = media_data['example']
                
                if 'examples' in media_data:
                    built_response['content'][media_type]['examples'] = media_data['examples']
        
        built_responses[status_code] = built_response
    
    return built_responses

def _build_schema(schema: Any) -> Dict:
    """
    Build schema object with support for:
    - Nested objects
    - Arrays
    - oneOf/anyOf/allOf
    - Discriminators
    - References
    """
    
    # Handle non-dict schemas
    if not isinstance(schema, dict):
        return {"type": "string"}
    
    # Handle $ref
    if '$ref' in schema:
        return schema
    
    built_schema = {}
    
    # Type
    if 'type' in schema:
        built_schema['type'] = schema['type']
    
    # Format
    if 'format' in schema:
        built_schema['format'] = schema['format']
    
    # Description
    if 'description' in schema:
        built_schema['description'] = schema['description']
    
    # Enum
    if 'enum' in schema:
        built_schema['enum'] = schema['enum']
    
    # Default
    if 'default' in schema:
        built_schema['default'] = schema['default']
    
    # Example
    if 'example' in schema:
        built_schema['example'] = schema['example']
    
    # Numeric constraints
    for key in ['minimum', 'maximum', 'exclusiveMinimum', 'exclusiveMaximum', 'multipleOf']:
        if key in schema:
            built_schema[key] = schema[key]
    
    # String constraints
    for key in ['minLength', 'maxLength', 'pattern']:
        if key in schema:
            built_schema[key] = schema[key]
    
    # Array constraints
    for key in ['minItems', 'maxItems', 'uniqueItems']:
        if key in schema:
            built_schema[key] = schema[key]
    
    # Object properties
    if 'properties' in schema:
        built_schema['properties'] = {}
        for prop_name, prop_schema in schema['properties'].items():
            built_schema['properties'][prop_name] = _build_schema(prop_schema)
    
    # Required fields
    if 'required' in schema:
        built_schema['required'] = schema['required']
    
    # Additional properties
    if 'additionalProperties' in schema:
        if isinstance(schema['additionalProperties'], bool):
            built_schema['additionalProperties'] = schema['additionalProperties']
        else:
            built_schema['additionalProperties'] = _build_schema(schema['additionalProperties'])
    
    # Array items
    if 'items' in schema:
        built_schema['items'] = _build_schema(schema['items'])
    
    # oneOf
    if 'oneOf' in schema:
        built_schema['oneOf'] = [_build_schema(s) for s in schema['oneOf']]
    
    # anyOf
    if 'anyOf' in schema:
        built_schema['anyOf'] = [_build_schema(s) for s in schema['anyOf']]
    
    # allOf
    if 'allOf' in schema:
        built_schema['allOf'] = [_build_schema(s) for s in schema['allOf']]
    
    # Discriminator
    if 'discriminator' in schema:
        built_schema['discriminator'] = schema['discriminator']
    
    # Nullable (OpenAPI 3.1.0)
    if 'nullable' in schema:
        # In OpenAPI 3.1.0, use type array instead
        if schema['nullable'] and 'type' in built_schema:
            built_schema['type'] = [built_schema['type'], 'null']
    
    return built_schema

def _build_components(components: Dict, endpoints: List[Dict]) -> Dict:
    """Build components object."""
    
    built_components = {
        "schemas": {},
        "securitySchemes": {}
    }
    
    # Add schemas from components
    if 'schemas' in components:
        for schema_name, schema_data in components['schemas'].items():
            built_components['schemas'][schema_name] = _build_schema(schema_data)
    
    # Extract and deduplicate schemas from endpoints
    extracted_schemas = _extract_schemas_from_endpoints(endpoints)
    for schema_name, schema_data in extracted_schemas.items():
        if schema_name not in built_components['schemas']:
            built_components['schemas'][schema_name] = schema_data
    
    # Add security schemes
    if 'securitySchemes' in components:
        built_components['securitySchemes'] = components['securitySchemes']
    
    return built_components

def _extract_schemas_from_endpoints(endpoints: List[Dict]) -> Dict:
    """Extract common schemas from endpoint definitions."""
    
    schemas = {}
    
    # This is a simplified version
    # In production, you'd want to analyze response/request schemas
    # and extract common patterns into reusable components
    
    return schemas

def _extract_tags(endpoints: List[Dict]) -> List[Dict]:
    """Extract unique tags from endpoints."""
    
    tags_set = set()
    for endpoint in endpoints:
        for tag in endpoint.get('tags', []):
            tags_set.add(tag)
    
    return [{"name": tag} for tag in sorted(tags_set)]

def _build_global_security(security_schemes: Dict) -> List[Dict]:
    """Build global security requirements."""
    
    # Return empty list - let each operation define its own security
    # Or return a default if you want global security
    return []

def validate_openapi_spec(spec: Dict) -> tuple[bool, List[str]]:
    """
    Validate OpenAPI specification.
    
    Returns:
        (is_valid, list_of_errors)
    """
    errors = []
    
    # Required top-level fields
    if 'openapi' not in spec:
        errors.append("Missing 'openapi' field")
    elif not spec['openapi'].startswith('3.'):
        errors.append(f"Invalid OpenAPI version: {spec['openapi']}")
    
    if 'info' not in spec:
        errors.append("Missing 'info' field")
    else:
        if 'title' not in spec['info']:
            errors.append("Missing 'info.title'")
        if 'version' not in spec['info']:
            errors.append("Missing 'info.version'")
    
    if 'paths' not in spec:
        errors.append("Missing 'paths' field")
    
    # Validate paths
    for path, path_item in spec.get('paths', {}).items():
        if not isinstance(path_item, dict):
            errors.append(f"Invalid path item for {path}")
            continue
        
        for method, operation in path_item.items():
            if method not in ['get', 'post', 'put', 'delete', 'patch', 'head', 'options', 'trace']:
                continue
            
            if not isinstance(operation, dict):
                errors.append(f"Invalid operation for {method.upper()} {path}")
            
            if 'responses' not in operation:
                errors.append(f"Missing responses for {method.upper()} {path}")
    
    return (len(errors) == 0, errors)