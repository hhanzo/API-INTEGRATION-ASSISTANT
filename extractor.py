"""
Dynamic API Documentation Extractor
Adapts to any documentation format and extracts complete endpoint specifications
"""

import json
from typing import Dict, Optional, List
from llm import GeminiClient
from scraper import WebScraper

class APIExtractor:
    def __init__(self):
        self.llm = GeminiClient()
        self.scraper = None
    
    def extract_from_url(self, url: str) -> Dict:
        """
        Dynamically extract API information from any URL.
        Auto-detects format and adjusts extraction strategy.
        """
        self.scraper = WebScraper(url)
        
        # Strategy 1: Try OpenAPI spec
        openapi_result = self._try_openapi(url)
        if openapi_result:
            return {
                'success': True,
                'method': 'openapi',
                'data': openapi_result,
                'error': None
            }
        
        # Strategy 2: Web scraping + LLM extraction
        html, error = self.scraper.fetch_page(url)
        if error:
            return {'success': False, 'error': error, 'data': None}
        
        # Detect documentation type and adjust prompt
        doc_type = self._detect_documentation_type(html, url)
        
        # Extract with context-aware prompt
        extracted = self._llm_extract_from_html(html, url, doc_type)
        
        if extracted:
            return {
                'success': True,
                'method': 'llm_extraction',
                'doc_type': doc_type,
                'data': extracted,
                'error': None
            }
        else:
            return {
                'success': False,
                'error': 'Could not extract API information',
                'data': None
            }
    
    def _try_openapi(self, url: str) -> Optional[Dict]:
        """Try to parse as OpenAPI spec."""
        from utils import fetch_api_spec, parse_api_spec
        
        spec, error = fetch_api_spec(url)
        if error or not spec:
            return None
        
        if 'openapi' not in spec and 'swagger' not in spec:
            return None
        
        parsed = parse_api_spec(spec)
        if 'error' in parsed:
            return None
        
        # Convert to our endpoint-centric format
        return self._convert_openapi_to_endpoint_format(parsed)
    
    def _detect_documentation_type(self, html: str, url: str) -> str:
        """
        Detect what type of documentation this is.
        Adjusts extraction strategy accordingly.
        """
        url_lower = url.lower()
        html_lower = html.lower()
        
        # GitHub Docs
        if 'docs.github.com' in url_lower or 'github.io' in url_lower:
            return 'github'
        
        # Stripe
        if 'stripe.com/docs' in url_lower:
            return 'stripe'
        
        # Readme.io platform
        if 'readme.io' in url_lower or 'readme-class' in html_lower:
            return 'readme'
        
        # Swagger UI
        if 'swagger-ui' in html_lower or 'redoc' in html_lower:
            return 'swagger_ui'
        
        # Generic REST API docs
        if any(word in html_lower for word in ['rest api', 'api reference', 'api documentation']):
            return 'generic_rest'
        
        return 'unknown'
    
    def _llm_extract_from_html(self, html: str, url: str, doc_type: str) -> Optional[Dict]:
        """Extract using LLM with context-aware prompting."""
        
        # Clean HTML
        cleaned = self.scraper.clean_html_for_llm(html, max_chars=40000)
        
        # Create context-aware prompt
        prompt = self._create_extraction_prompt(cleaned, url, doc_type)
        
        # Get LLM response with retry
        max_retries = 2
        for attempt in range(max_retries):
            result = self.llm.analyze_apis(prompt)
            
            if result['error']:
                if attempt < max_retries - 1:
                    continue
                print(f"LLM Error after {max_retries} attempts: {result['error']}")
                return None
            
            if result['parsed']:
                # Validate and clean the response
                return self._validate_and_clean_response(result['parsed'])
        
        return None
    
    def _create_extraction_prompt(self, cleaned_html: str, url: str, doc_type: str) -> str:
        """Create dynamic, context-aware extraction prompt."""
        
        # Base instructions
        base_instructions = """You are an expert API documentation analyzer. Your task is to extract COMPLETE endpoint specifications including all request/response schemas and error codes.

CRITICAL: Extract information EXACTLY as it appears in the documentation. Do not invent or assume anything not explicitly stated."""

        # Documentation-specific guidance
        doc_specific_guidance = {
            'github': """
This is GitHub documentation. It typically has:
- Multiple endpoints on one page
- Endpoints grouped by resource type
- Parameters in tables
- Response examples in JSON
- Status codes listed separately
Extract EACH endpoint separately - do not merge them.""",
            
            'stripe': """
This is Stripe documentation. It typically has:
- One main endpoint per page
- Deep nested object schemas
- Expandable parameters
- Rich error responses
- Metadata objects
Pay special attention to nested objects and all possible error codes.""",
            
            'readme': """
This is Readme.io documentation. It typically has:
- Clean structure with code examples
- Request/response on same page
- Clear parameter tables
Extract from both prose and code examples.""",
            
            'generic_rest': """
This appears to be standard REST API documentation.
Extract from whatever structure is present - tables, code examples, or prose.""",
            
            'unknown': """
Documentation format is unclear. Extract from any available structure:
- Look for HTTP methods (GET, POST, PUT, DELETE, PATCH)
- Look for URL paths
- Extract from code examples, tables, or text
Be thorough and capture all available information."""
        }
        
        guidance = doc_specific_guidance.get(doc_type, doc_specific_guidance['unknown'])
        
        # The extraction schema - NOTE: NOT using f-string here to avoid escaping issues
        schema_spec = """
{
  "api_info": {
    "name": "API name from page title",
    "base_url": "https://api.example.com (extract from examples or text)",
    "description": "Brief description",
    "version": "version if mentioned"
  },
  
  "endpoints": [
    {
      "method": "GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS",
      "path": "/v1/resource/{id}",
      "summary": "Brief one-line description",
      "description": "Detailed description",
      "operation_id": "operationId if present",
      "tags": ["resource", "category"],
      
      "parameters": [
        {
          "name": "id",
          "in": "path|query|header|cookie",
          "description": "Parameter description",
          "required": true|false,
          "schema": {
            "type": "string|integer|boolean|array|object|number",
            "format": "int32|int64|float|double|byte|binary|date|date-time|password|email|uuid",
            "enum": ["value1", "value2"],
            "default": "default value",
            "minimum": 0,
            "maximum": 100,
            "pattern": "regex pattern",
            "items": {"type": "string"},
            "properties": {}
          },
          "example": "example-value"
        }
      ],
      
      "request_body": {
        "description": "Request body description",
        "required": true|false,
        "content": {
          "application/json": {
            "schema": {
              "type": "object",
              "required": ["field1", "field2"],
              "properties": {
                "field_name": {
                  "type": "string|integer|boolean|array|object|number",
                  "description": "Field description",
                  "format": "date-time|email|uuid|etc",
                  "enum": ["option1", "option2"],
                  "items": {
                    "type": "string",
                    "enum": ["val1", "val2"]
                  },
                  "properties": {
                    "nested_field": {
                      "type": "string",
                      "description": "Nested field"
                    }
                  },
                  "oneOf": [
                    {"type": "string"},
                    {"type": "integer"}
                  ],
                  "anyOf": [],
                  "allOf": []
                }
              }
            },
            "example": {
              "field_name": "example value"
            },
            "examples": {
              "example1": {
                "summary": "Example scenario",
                "value": {}
              }
            }
          }
        }
      },
      
      "responses": {
        "200": {
          "description": "Success response description",
          "headers": {
            "X-Rate-Limit": {
              "description": "Rate limit info",
              "schema": {"type": "integer"}
            }
          },
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "id": {"type": "string", "description": "Resource ID"},
                  "data": {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": true
                  }
                }
              },
              "example": {}
            }
          }
        },
        "201": {"description": "Created", "content": {}},
        "204": {"description": "No content"},
        "400": {
          "description": "Bad request - validation failed",
          "content": {
            "application/json": {
              "schema": {
                "type": "object",
                "properties": {
                  "error": {
                    "type": "object",
                    "properties": {
                      "code": {"type": "string"},
                      "message": {"type": "string"},
                      "details": {"type": "array", "items": {"type": "object"}}
                    }
                  }
                }
              },
              "example": {
                "error": {
                  "code": "invalid_request",
                  "message": "Validation failed",
                  "details": [{"field": "email", "message": "Invalid format"}]
                }
              }
            }
          }
        },
        "401": {"description": "Unauthorized", "content": {}},
        "403": {"description": "Forbidden", "content": {}},
        "404": {"description": "Not found", "content": {}},
        "409": {"description": "Conflict", "content": {}},
        "422": {"description": "Unprocessable entity", "content": {}},
        "429": {
          "description": "Rate limit exceeded",
          "headers": {
            "Retry-After": {
              "description": "Seconds to wait",
              "schema": {"type": "integer"}
            },
            "X-RateLimit-Limit": {"schema": {"type": "integer"}},
            "X-RateLimit-Remaining": {"schema": {"type": "integer"}},
            "X-RateLimit-Reset": {"schema": {"type": "integer"}}
          },
          "content": {}
        },
        "500": {"description": "Internal server error", "content": {}},
        "502": {"description": "Bad gateway", "content": {}},
        "503": {"description": "Service unavailable", "content": {}}
      },
      
      "security": [
        {"bearerAuth": []},
        {"apiKey": []}
      ],
      
      "x-code-samples": [
        {
          "lang": "curl",
          "source": "curl command"
        },
        {
          "lang": "python",
          "source": "python code"
        }
      ]
    }
  ],
  
  "components": {
    "schemas": {
      "ResourceName": {
        "type": "object",
        "description": "Schema description",
        "required": ["id", "name"],
        "properties": {
          "id": {
            "type": "string",
            "description": "Unique identifier",
            "format": "uuid",
            "example": "123e4567-e89b-12d3-a456-426614174000"
          },
          "name": {"type": "string"},
          "nested_object": {
            "type": "object",
            "properties": {
              "field": {"type": "string"}
            }
          },
          "array_field": {
            "type": "array",
            "items": {
              "type": "object",
              "properties": {
                "item_field": {"type": "string"}
              }
            }
          },
          "discriminated_field": {
            "oneOf": [
              {"$ref": "#/components/schemas/Type1"},
              {"$ref": "#/components/schemas/Type2"}
            ],
            "discriminator": {
              "propertyName": "type",
              "mapping": {
                "type1": "#/components/schemas/Type1",
                "type2": "#/components/schemas/Type2"
              }
            }
          }
        }
      }
    },
    "securitySchemes": {
      "bearerAuth": {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "JWT token authentication"
      },
      "apiKey": {
        "type": "apiKey",
        "in": "header",
        "name": "X-API-Key",
        "description": "API key authentication"
      },
      "oauth2": {
        "type": "oauth2",
        "flows": {
          "authorizationCode": {
            "authorizationUrl": "https://example.com/oauth/authorize",
            "tokenUrl": "https://example.com/oauth/token",
            "scopes": {
              "read": "Read access",
              "write": "Write access"
            }
          }
        }
      }
    }
  },
  
  "needs_more_pages": true|false,
  "suggested_urls": ["url1", "url2", "url3"]
}
"""

        # Construct the final prompt using regular string concatenation
        prompt = base_instructions + "\n\n" + guidance + "\n\n"
        prompt += f"URL: {url}\n\n"
        prompt += "Documentation Content:\n"
        prompt += cleaned_html + "\n\n"
        prompt += "Extract and return valid JSON matching this structure:\n"
        prompt += schema_spec + "\n\n"
        
        prompt += """
EXTRACTION RULES:

1. **Deep Schema Extraction**:
   - Extract ALL nested objects (don't stop at top level)
   - Capture array item schemas
   - Extract discriminators for polymorphic types
   - Use oneOf/anyOf/allOf where docs show alternatives

2. **Complete Error Coverage**:
   - Extract EVERY HTTP status code mentioned
   - Include error response schemas
   - Capture error headers (Retry-After, X-RateLimit-*)
   - Note retry strategies

3. **Type Inference**:
   - "email@example.com" → type: "string", format: "email"
   - "2024-01-15T10:30:00Z" → type: "string", format: "date-time"
   - "550e8400-e29b-41d4-a716-446655440000" → format: "uuid"
   - 123 → type: "integer"
   - 123.45 → type: "number"
   - true/false → type: "boolean"
   - [...] → type: "array", extract items schema
   - {...} → type: "object", extract properties

4. **Parameter Locations**:
   - URL parameters like /users/{id} → in: "path"
   - Query strings like ?limit=10 → in: "query"
   - Headers like Authorization → in: "header"
   - Body fields → in request_body

5. **Multi-Endpoint Pages**:
   - If page describes multiple endpoints, create separate entries
   - Do NOT merge different endpoints together
   - Each HTTP method + path combination = separate endpoint

6. **Code Examples**:
   - Extract curl, Python, JavaScript examples
   - Store in x-code-samples

7. **Reusable Schemas**:
   - If same object structure appears multiple times, create in components/schemas
   - Reference using $ref syntax

Return ONLY valid JSON. No markdown code blocks, no explanations.

JSON:"""

        return prompt
    
    def _validate_and_clean_response(self, response: Dict) -> Dict:
        """Validate and normalize the LLM response."""
        
        # Ensure required top-level keys
        if 'endpoints' not in response:
            response['endpoints'] = []
        
        if 'components' not in response:
            response['components'] = {'schemas': {}, 'securitySchemes': {}}
        
        if 'api_info' not in response:
            response['api_info'] = {
                'name': 'Unknown API',
                'base_url': '',
                'description': '',
                'version': '1.0.0'
            }
        
        # Clean and validate each endpoint
        cleaned_endpoints = []
        for ep in response.get('endpoints', []):
            if self._is_valid_endpoint(ep):
                cleaned_ep = self._normalize_endpoint(ep)
                cleaned_endpoints.append(cleaned_ep)
        
        response['endpoints'] = cleaned_endpoints
        
        return response
    
    def _is_valid_endpoint(self, ep: Dict) -> bool:
        """Check if endpoint has minimum required fields."""
        return (
            'method' in ep and 
            'path' in ep and
            ep['method'] in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']
        )
    
    def _normalize_endpoint(self, ep: Dict) -> Dict:
        """Normalize endpoint structure to OpenAPI 3.1.0 compatible format."""
        raw_path = ep.get('path')
        path = raw_path if isinstance(raw_path, str) and raw_path.strip() else '/'  

        normalized = {
            'method': ep['method'].upper(),
            'path': path,
            'summary': ep.get('summary', ''),
            'description': ep.get('description', ''),
            'operation_id': ep.get('operation_id', ''),
            'tags': ep.get('tags', []),
            'parameters': ep.get('parameters', []),
            'request_body': ep.get('request_body', {}),
            'responses': ep.get('responses', {}),
            'security': ep.get('security', []),
            'x-code-samples': ep.get('x-code-samples', [])
        }
        
        # Ensure responses has at least one entry
        if not normalized['responses']:
            normalized['responses'] = {
                '200': {
                    'description': 'Successful response',
                    'content': {
                        'application/json': {
                            'schema': {'type': 'object'}
                        }
                    }
                }
            }
        
        return normalized
    
    def _convert_openapi_to_endpoint_format(self, openapi_spec: Dict) -> Dict:
        """Convert existing OpenAPI spec to our endpoint-centric format."""
        
        result = {
            'api_info': {
                'name': openapi_spec.get('info', {}).get('title', 'Unknown'),
                'base_url': openapi_spec.get('base_url', ''),
                'description': openapi_spec.get('info', {}).get('description', ''),
                'version': openapi_spec.get('info', {}).get('version', '1.0.0')
            },
            'endpoints': [],
            'components': {
                'schemas': openapi_spec.get('schemas', {}),
                'securitySchemes': openapi_spec.get('auth', {})
            }
        }
        
        # Convert endpoints
        for ep in openapi_spec.get('endpoints', []):
            converted_ep = {
                'method': ep['method'],
                'path': ep['path'],
                'summary': ep.get('summary', ''),
                'description': ep.get('description', ''),
                'parameters': [],
                'responses': {}
            }
            
            result['endpoints'].append(converted_ep)
        
        return result