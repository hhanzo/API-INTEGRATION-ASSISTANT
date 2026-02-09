from utils import fetch_api_spec, parse_api_spec
from llm import GeminiClient
from prompts import create_mapping_prompt
import json

# Use two similar APIs
api_a_url = "https://petstore.swagger.io/v2/swagger.json"
api_b_url = "https://petstore3.swagger.io/api/v3/openapi.json"

print("Fetching APIs...")
spec_a, _ = fetch_api_spec(api_a_url)
spec_b, _ = fetch_api_spec(api_b_url)

print("Parsing...")
parsed_a = parse_api_spec(spec_a)
parsed_b = parse_api_spec(spec_b)

print("Creating prompt...")
prompt = create_mapping_prompt(parsed_a, parsed_b)

print("\n" + "="*60)
print("PROMPT PREVIEW (first 500 chars):")
print("="*60)
print(prompt[:500] + "...\n")

print("Sending to Gemini...")
client = GeminiClient()
result = client.analyze_apis(prompt)

if result['error']:
    print(f"❌ Error: {result['error']}")
else:
    print("✅ Gemini Response:")
    print("="*60)
    
    # Try to parse as JSON
    try:
        mappings = json.loads(result['response'])
        print(json.dumps(mappings, indent=2))
    except json.JSONDecodeError:
        print("Raw response (not valid JSON):")
        print(result['response'])