import json
from typing import Dict, Optional

from click import prompt

from typer import prompt
from llm import GeminiClient
from scraper import WebScraper

class APIExtractor:
    def __init__(self):
        self.llm = GeminiClient()
        self.scraper = None
    
    def extract_from_url(self, url: str) -> Dict:
        """
        Extract API information from a single URL.
        Tries OpenAPI first, then falls back to web scraping + LLM.
        """
        # Initialize scraper for this domain
        self.scraper = WebScraper(url)
        
        # Strategy 1: Try as OpenAPI spec
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
        
        # Extract with LLM
        extracted = self._llm_extract_from_html(html, url)
        
        if extracted:
            return {
                'success': True,
                'method': 'llm_extraction',
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
        
        # Check if it's actually OpenAPI
        if 'openapi' not in spec and 'swagger' not in spec:
            return None
        
        parsed = parse_api_spec(spec)
        if 'error' in parsed:
            return None
        
        return parsed
    
    def _llm_extract_from_html(self, html: str, url: str) -> Optional[Dict]:
        """Use LLM to extract API info from HTML."""
        
        # Clean HTML
        cleaned = self.scraper.clean_html_for_llm(html)
        
        # Create extraction prompt
        prompt = self._create_extraction_prompt(cleaned, url)
        
        # Get LLM response
        result = self.llm.analyze_apis(prompt)
        
        if result['error']:
            print(f"LLM Error: {result['error']}")
            return None
        
        return result['parsed']
    
    def _create_extraction_prompt(self, cleaned_html: str, url: str) -> str:
        return f"""
You are an expert at reading API documentation and producing OpenAPI-style structured data.

URL:
{url}

Documentation content:
{cleaned_html}

Return a single JSON object with the EXACT structure described below.

The extraction must be:
- endpoint-centric
- error-aware
- schema-rich (recursive)

==============================
JSON OUTPUT STRUCTURE
==============================

{{
  "api_info": {{
    "name": "API name if available",
    "base_url": "Base API URL if mentioned",
    "description": "Short description of the API",
    "version": "Version if available"
  }},

  "endpoints": [
    {{
      "method": "GET|POST|PUT|PATCH|DELETE",
      "path": "/resource/path",
      "description": "What this endpoint does",

      "request": {{
        "content_type": "application/json or other if stated",

        "parameters": [
          {{
            "name": "parameter name",
            "location": "path|query|header|cookie",
            "type": "string|integer|boolean|number|array|object",
            "required": true,
            "description": "parameter meaning",
            "example": "example value"
          }}
        ],

        "schema": <SCHEMA_OBJECT or null>,
        "example": <JSON example or null>
      }},

      "responses": {{
        "200": {{
          "description": "response description",
          "content_type": "application/json if known",
          "schema": <SCHEMA_OBJECT or null>,
          "example": <JSON example or null>
        }},
        "400": {{
          "description": "error description",
          "content_type": "application/json if known",
          "schema": <SCHEMA_OBJECT or null>,
          "example": <JSON example or null>
        }}
      }},

      "error_handling": {{
        "rate_limit": "rate limit information if documented",
        "retry_logic": "retry or backoff guidance if mentioned",
        "idempotency": "idempotency key support if mentioned"
      }}
    }}
  ],

  "common_schemas": {{
    "SchemaName": <SCHEMA_OBJECT>
  }},

  "authentication": {{
    "type": "bearer|api_key|oauth2|basic|none",
    "description": "how authentication works",
    "location": "header|query|cookie",
    "parameter_name": "Authorization or api_key etc"
  }},

  "needs_more_pages": true,
  "suggested_urls": ["url1", "url2"]
}}

==============================
SCHEMA_OBJECT FORMAT
==============================

All request and response schemas MUST follow JSON Schema / OpenAPI style.

A schema object may contain:

- type
- description
- example
- properties   (for objects)
- items        (for arrays)
- required     (array of property names)
- enum
- oneOf
- allOf
- anyOf
- nullable

Nested objects MUST be represented recursively using "properties".
Arrays MUST use "items".

Examples:

Object:
{{
  "type": "object",
  "properties": {{
    "id": {{ "type": "string" }},
    "profile": {{
      "type": "object",
      "properties": {{
        "name": {{ "type": "string" }},
        "age": {{ "type": "integer" }}
      }},
      "required": ["name"]
    }}
  }},
  "required": ["id"]
}}

Array:
{{
  "type": "array",
  "items": {{
    "type": "object",
    "properties": {{
      "id": {{ "type": "string" }}
    }}
  }}
}}

oneOf example:
{{
  "oneOf": [
    {{ "type": "object", "properties": {{ "user_id": {{ "type": "string" }} }} }},
    {{ "type": "object", "properties": {{ "org_id": {{ "type": "string" }} }} }}
  ]
}}

==============================
IMPORTANT EXTRACTION RULES
==============================

1. Each documentation section usually describes one endpoint.
   If a section contains multiple endpoints, extract them separately.

2. Extract EACH endpoint independently.

3. Attach request schema ONLY to that endpoint.

4. Extract responses PER HTTP STATUS CODE.

5. Extract all mentioned status codes (2xx, 3xx, 4xx, 5xx).

6. If a response example is shown, build its schema from that example,
   preserving nested structure.

7. Use oneOf / allOf / anyOf ONLY if the documentation explicitly indicates
   alternative or composed response shapes.

8. If a schema is not described or cannot be inferred, use null.

9. Do NOT invent fields, endpoints, or schemas.

10. If authentication or error behavior is described globally, still include it
    in this page-level output.

11. If information is missing, omit the field or use null. Do not guess.

Return ONLY valid JSON.
"""
        return prompt
#     def _create_extraction_prompt(self, cleaned_html: str, url: str) -> str:
#         return f"""
# You are an expert in reading API documentation.

# Extract API information from the following documentation page.

# URL:
# {url}

# Documentation content:
# {cleaned_html}

# Return a JSON object using the EXACT structure below.

# The extraction MUST be endpoint-centric and error-aware.

# JSON STRUCTURE:

# {{
#   "api_info": {{
#     "name": "API name if available",
#     "base_url": "Base API URL if mentioned",
#     "description": "Short description of the API",
#     "version": "Version if available"
#   }},

#   "endpoints": [
#     {{
#       "method": "GET|POST|PUT|PATCH|DELETE",
#       "path": "/resource/path",
#       "description": "What this endpoint does",

#       "request": {{
#         "content_type": "application/json or other if stated",

#         "parameters": [
#           {{
#             "name": "parameter name",
#             "location": "path|query|header|body",
#             "type": "string|integer|boolean|array|object",
#             "required": true,
#             "description": "parameter meaning",
#             "example": "example value"
#           }}
#         ],

#         "schema": {{
#           "field_name": {{
#             "type": "string|integer|boolean|array|object",
#             "required": true,
#             "description": "field description",
#             "example": "example value"
#           }}
#         }},

#         "example": {{}}
#       }},

#       "responses": {{
#         "200": {{
#           "description": "success description",
#           "content_type": "application/json if known",

#           "schema": {{
#             "field_name": {{
#               "type": "string|integer|boolean|array|object",
#               "description": "field description"
#             }}
#           }},

#           "example": {{}}
#         }},

#         "400": {{
#           "description": "client error description",

#           "schema": {{
#             "error": {{
#               "type": "object",
#               "properties": {{
#                 "message": {{ "type": "string" }},
#                 "code": {{ "type": "string" }}
#               }}
#             }}
#           }},

#           "example": {{}}
#         }}
#       }},

#       "error_handling": {{
#         "rate_limit": "rate limit information if documented",
#         "retry_logic": "retry or backoff guidance if mentioned",
#         "idempotency": "idempotency key support if mentioned"
#       }}
#     }}
#   ],

#   "common_schemas": {{
#     "SchemaName": {{
#       "description": "schema meaning",
#       "properties": {{
#         "field": {{
#           "type": "string|integer|boolean|array|object",
#           "description": "field description"
#         }}
#       }}
#     }}
#   }},

#   "authentication": {{
#     "type": "bearer|api_key|oauth2|basic|none",
#     "description": "how to authenticate",
#     "location": "header|query|body",
#     "parameter_name": "Authorization or api_key etc"
#   }},

#   "needs_more_pages": true,
#   "suggested_urls": ["url1", "url2"]
# }}

# IMPORTANT EXTRACTION RULES:

# 1. The page may contain multiple endpoint sections. Treat each section independently and extract one endpoint per section.
# 2. Extract EACH endpoint separately.
# 3. Attach request schema ONLY to that endpoint.
# 4. Extract response schemas PER HTTP STATUS CODE.
# 5. Extract ALL mentioned status codes (2xx, 4xx, 5xx).
# 6. If a status code has an example, build its schema from that example.
# 7. If the documentation describes errors globally, still include those error responses inside each endpoint where applicable.
# 8. Infer types from examples when necessary.
# 9. If information is not present, omit the field.
# 10. Do NOT invent endpoints, parameters or fields.

# Return ONLY valid JSON.
# """

        
#         return prompt
