import requests
import yaml
import json
from typing import Dict, Optional, Tuple
from typing import List

def fetch_api_spec(url_or_text: str) -> Tuple[Optional[Dict], Optional[str]]:
    """
    Fetch API spec from URL or parse raw JSON/YAML text.
    
    Returns:
        Tuple of (spec_dict, error_message)
    """
    # Check if input is a URL
    if url_or_text.strip().startswith('http'):
        return _fetch_from_url(url_or_text)
    else:
        return _parse_raw_spec(url_or_text)

def _fetch_from_url(url: str) -> Tuple[Optional[Dict], Optional[str]]:
    """Fetch spec from URL with detailed error reporting."""
    try:
        # Add headers to mimic a browser request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, application/yaml, text/yaml, */*'
        }
        
        response = requests.get(url, timeout=15, headers=headers)
        
        # Check status code
        if response.status_code == 404:
            return None, f"URL not found (404). Please verify the URL is correct: {url}"
        elif response.status_code == 403:
            return None, f"Access forbidden (403). The API might require authentication."
        elif response.status_code >= 400:
            return None, f"HTTP Error {response.status_code}: {response.reason}"
        
        response.raise_for_status()
        
        # Try parsing as JSON first
        try:
            spec = response.json()
            return spec, None
        except json.JSONDecodeError:
            # Try YAML
            try:
                spec = yaml.safe_load(response.text)
                return spec, None
            except yaml.YAMLError as e:
                return None, f"Failed to parse response as JSON or YAML: {str(e)}"
            
    except requests.Timeout:
        return None, f"Request timed out after 15 seconds. The server might be slow or unreachable."
    except requests.ConnectionError:
        return None, f"Could not connect to {url}. Please check your internet connection."
    except requests.HTTPError as e:
        return None, f"HTTP Error {e.response.status_code}: {e.response.reason}"
    except Exception as e:
        return None, f"Unexpected error: {str(e)}"
    
def _parse_raw_spec(text: str) -> Tuple[Optional[Dict], Optional[str]]:
    """Parse raw JSON or YAML text."""
    try:
        # Try JSON first
        spec = json.loads(text)
        return spec, None
    except json.JSONDecodeError:
        try:
            # Try YAML
            spec = yaml.safe_load(text)
            return spec, None
        except yaml.YAMLError as e:
            return None, f"Invalid JSON/YAML format: {str(e)}"

def detect_openapi_version(spec: Dict) -> Tuple[str, Optional[str]]:
    """
    Detect OpenAPI/Swagger version.
    
    Returns:
        Tuple of (version, error_message)
    """
    if 'swagger' in spec:
        version = spec['swagger']
        if version.startswith('2'):
            return '2.0', None
        else:
            return version, f"Unsupported Swagger version: {version}"
    
    elif 'openapi' in spec:
        version = spec['openapi']
        if version.startswith('3.0'):
            return '3.0', None
        elif version.startswith('3.1'):
            return '3.1', None
        else:
            return version, f"Unsupported OpenAPI version: {version}"
    
    else:
        return 'unknown', "Could not detect API spec version"

def validate_spec(spec: Dict) -> Optional[str]:
    """
    Validate basic structure of API spec.
    
    Returns:
        Error message if invalid, None if valid
    """
    if not isinstance(spec, dict):
        return "Spec must be a JSON object"
    
    if 'info' not in spec:
        return "Missing 'info' section"
    
    if 'paths' not in spec:
        return "Missing 'paths' section"
    
    return None

def extract_endpoints(spec: Dict, version: str) -> List[Dict]:
    """
    Extract all endpoints from the API spec.
    
    Returns:
        List of endpoint dictionaries with method, path, summary
    """
    endpoints = []
    paths = spec.get('paths', {})
    
    for path, methods in paths.items():
        for method, details in methods.items():
            # Skip non-HTTP methods (parameters, servers, etc.)
            if method not in ['get', 'post', 'put', 'patch', 'delete', 'head', 'options']:
                continue
            
            endpoint = {
                'path': path,
                'method': method.upper(),
                'summary': details.get('summary', ''),
                'description': details.get('description', ''),
                'operationId': details.get('operationId', ''),
                'tags': details.get('tags', [])
            }
            endpoints.append(endpoint)
    
    return endpoints

def extract_schemas(spec: Dict, version: str) -> Dict:
    """
    Extract data models/schemas from the spec.
    
    Returns:
        Dictionary of schema definitions
    """
    schemas = {}
    
    if version == '2.0':
        # Swagger 2.0 uses 'definitions'
        schemas = spec.get('definitions', {})
    else:
        # OpenAPI 3.x uses 'components/schemas'
        schemas = spec.get('components', {}).get('schemas', {})
    
    # Simplify schemas for LLM consumption
    simplified_schemas = {}
    for schema_name, schema_def in schemas.items():
        simplified_schemas[schema_name] = _simplify_schema(schema_def)
    
    return simplified_schemas

def _simplify_schema(schema: Dict) -> Dict:
    """Simplify schema to just properties and types."""
    properties = schema.get('properties', {})
    required = schema.get('required', [])
    
    simplified = {}
    for prop_name, prop_def in properties.items():
        simplified[prop_name] = {
            'type': prop_def.get('type', 'unknown'),
            'format': prop_def.get('format'),
            'description': prop_def.get('description'),
            'required': prop_name in required,
            'enum': prop_def.get('enum')
        }
    
    return simplified

def extract_auth_info(spec: Dict, version: str) -> Dict:
    """Extract authentication/security information."""
    auth_info = {
        'schemes': [],
        'details': {}
    }
    
    if version == '2.0':
        # Swagger 2.0
        security_defs = spec.get('securityDefinitions', {})
        for name, details in security_defs.items():
            auth_info['schemes'].append(details.get('type', 'unknown'))
            auth_info['details'][name] = details
    else:
        # OpenAPI 3.x
        security_schemes = spec.get('components', {}).get('securitySchemes', {})
        for name, details in security_schemes.items():
            auth_info['schemes'].append(details.get('type', 'unknown'))
            auth_info['details'][name] = details
    
    return auth_info

def parse_api_spec(spec: Dict) -> Dict:
    """
    Main parser that extracts all relevant information.
    
    Returns:
        Dictionary with endpoints, schemas, auth, metadata
    """
    # Detect version
    version, error = detect_openapi_version(spec)
    if error:
        return {'error': error}
    
    # Validate spec
    validation_error = validate_spec(spec)
    if validation_error:
        return {'error': validation_error}
    
    # Extract all components
    parsed = {
        'version': version,
        'info': {
            'title': spec.get('info', {}).get('title', 'Unknown'),
            'version': spec.get('info', {}).get('version', 'Unknown'),
            'description': spec.get('info', {}).get('description', '')
        },
        'base_url': _extract_base_url(spec, version),
        'endpoints': extract_endpoints(spec, version),
        'schemas': extract_schemas(spec, version),
        'auth': extract_auth_info(spec, version)
    }
    
    return parsed

def _extract_base_url(spec: Dict, version: str) -> str:
    """Extract base URL from spec."""
    if version == '2.0':
        host = spec.get('host', '')
        base_path = spec.get('basePath', '')
        schemes = spec.get('schemes', ['https'])
        return f"{schemes[0]}://{host}{base_path}"
    else:
        servers = spec.get('servers', [])
        return servers[0].get('url', '') if servers else ''
    
