import json
from typing import Dict, Optional
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
You are an expert in reading API documentation.

Extract API information from the following documentation page.

URL:
{url}

Documentation content:
{cleaned_html}

Return a JSON object using the EXACT structure below.

The extraction MUST be endpoint-centric and error-aware.

JSON STRUCTURE:

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
            "location": "path|query|header|body",
            "type": "string|integer|boolean|array|object",
            "required": true,
            "description": "parameter meaning",
            "example": "example value"
          }}
        ],

        "schema": {{
          "field_name": {{
            "type": "string|integer|boolean|array|object",
            "required": true,
            "description": "field description",
            "example": "example value"
          }}
        }},

        "example": {{}}
      }},

      "responses": {{
        "200": {{
          "description": "success description",
          "content_type": "application/json if known",

          "schema": {{
            "field_name": {{
              "type": "string|integer|boolean|array|object",
              "description": "field description"
            }}
          }},

          "example": {{}}
        }},

        "400": {{
          "description": "client error description",

          "schema": {{
            "error": {{
              "type": "object",
              "properties": {{
                "message": {{ "type": "string" }},
                "code": {{ "type": "string" }}
              }}
            }}
          }},

          "example": {{}}
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
    "SchemaName": {{
      "description": "schema meaning",
      "properties": {{
        "field": {{
          "type": "string|integer|boolean|array|object",
          "description": "field description"
        }}
      }}
    }}
  }},

  "authentication": {{
    "type": "bearer|api_key|oauth2|basic|none",
    "description": "how to authenticate",
    "location": "header|query|body",
    "parameter_name": "Authorization or api_key etc"
  }},

  "needs_more_pages": true,
  "suggested_urls": ["url1", "url2"]
}}

IMPORTANT EXTRACTION RULES:

1. Extract EACH endpoint separately.
2. Attach request schema ONLY to that endpoint.
3. Extract response schemas PER HTTP STATUS CODE.
4. Extract ALL mentioned status codes (2xx, 4xx, 5xx).
5. If a status code has an example, build its schema from that example.
6. If the documentation describes errors globally, still include those error responses inside each endpoint where applicable.
7. Infer types from examples when necessary.
8. If information is not present, omit the field.
9. Do NOT invent endpoints, parameters or fields.

Return ONLY valid JSON.
"""

        
    return prompt