from utils import fetch_api_spec, parse_api_spec
import json

# Test with Petstore API
spec, error = fetch_api_spec("https://petstore.swagger.io/v2/swagger.json")
if error:
    print(f"Fetch error: {error}")
    exit()

parsed = parse_api_spec(spec)

print("=" * 50)
print(f"API: {parsed['info']['title']}")
print(f"Version: {parsed['version']}")
print(f"Base URL: {parsed['base_url']}")
print(f"Auth Schemes: {parsed['auth']['schemes']}")
print(f"\nEndpoints ({len(parsed['endpoints'])} total):")
for ep in parsed['endpoints'][:5]:  # Show first 5
    print(f"  {ep['method']} {ep['path']} - {ep['summary']}")
print(f"\nSchemas ({len(parsed['schemas'])} total):")
for schema_name in list(parsed['schemas'].keys())[:3]:  # Show first 3
    print(f"  - {schema_name}")
    for field, details in list(parsed['schemas'][schema_name].items())[:3]:
        print(f"      {field}: {details['type']}")