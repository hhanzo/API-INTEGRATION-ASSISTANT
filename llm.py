import google.generativeai as genai
import os
from dotenv import load_dotenv
import json
from typing import Dict, Optional
import time
import re 

load_dotenv()

class GeminiClient:
    def __init__(self):
        api_key = os.getenv('GEMINI_API_KEY')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not found in environment")
        
        # Configure Gemini
        genai.configure(api_key=api_key)
        
        # Use Gemini 1.5 Pro for best results
        #self.model = genai.GenerativeModel('gemini-3-flash-preview')
        self.model = genai.GenerativeModel('gemma-3-12b-it')
        #for model in genai.list_models():
         #   print(f"Available model: {model.name}")

        # Generation config
        self.generation_config = {
            'temperature': 0.2,  # Lower for more deterministic output
            'top_p': 0.8,
            'top_k': 40,
            'max_output_tokens': 8192,
        }
        
        # Safety settings (permissive for API specs)
        self.safety_settings = [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_NONE"
            }
        ]
    

    def analyze_apis(self, prompt: str, max_retries: int = 3) -> Dict:
        """
        Send prompt to Gemini and get structured response.
        
        Args:
            prompt: The analysis prompt
            max_retries: Number of retry attempts for failed requests
            
        Returns:
            Dict with 'response', 'parsed', and 'error' keys
        """
        last_error = None
        
        for attempt in range(max_retries):
            try:
                # Generate response
                response = self.model.generate_content(
                    prompt,
                    generation_config=self.generation_config,
                    safety_settings=self.safety_settings
                )
                
                # Check if response was blocked
                if not response.text:
                    return {
                        'response': None,
                        'parsed': None,
                        'error': 'Response was blocked by safety filters. Try rephrasing the prompt.'
                    }
                
                response_text = response.text
                
                # Try to parse as JSON
                parsed_json = self._parse_json_response(response_text)
                
                return {
                    'response': response_text,
                    'parsed': parsed_json,
                    'error': None
                }
            
            except Exception as e:
                error_msg = str(e)
                last_error = error_msg
                
                # Check for quota/rate limit errors
                if 'quota' in error_msg.lower() or 'rate' in error_msg.lower():
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt  # Exponential backoff
                        print(f"Rate limited. Waiting {wait_time}s before retry...")
                        time.sleep(wait_time)
                        continue
                
                # Check for API errors
                if 'API' in error_msg or '500' in error_msg:
                    if attempt < max_retries - 1:
                        time.sleep(1)
                        continue
                
                # For other errors, don't retry
                break
        
        return {
            'response': None,
            'parsed': None,
            'error': f'Failed after {max_retries} attempts. Last error: {last_error}'
        }
    
    def _parse_json_response(self, response_text: str) -> Optional[Dict]:
        """
        Extract JSON from Gemini's response, handling markdown and other formatting.
        """
        import re
        
        # Try direct JSON parse first
        try:
            return json.loads(response_text)
        except json.JSONDecodeError:
            pass
        
        # Try to extract JSON from markdown code blocks
        # Pattern 1: ```json ... ```
        json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Pattern 2: ``` ... ``` (without json label)
        json_match = re.search(r'```\s*(\{.*?\})\s*```', response_text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Try to find any JSON object in the text
        json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass
        
        return None
    
    def test_connection(self) -> bool:
        """Test if the API key is valid and working."""
        try:
            response = self.model.generate_content(
                "Say 'Hello from Gemini!' and nothing else.",
                generation_config={'max_output_tokens': 100}
            )
            return response.text is not None
        except Exception as e:
            print(f"Connection test failed: {str(e)}")
            return False


def parse_json_response(response_text: str) -> Optional[Dict]:
    """
    Extract JSON from Claude's response, even if wrapped in markdown or text.
    """
    # Try direct JSON parse first
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass
    
    # Try to extract JSON from markdown code blocks
    json_match = re.search(r'```json\s*(\{.*?\})\s*```', response_text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass
    
    # Try to find any JSON object in the text
    json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except json.JSONDecodeError:
            pass
    
    return None
