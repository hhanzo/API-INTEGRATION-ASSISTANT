from extractor import APIExtractor
import json

print("=" * 70)
print("TESTING SINGLE-PAGE API EXTRACTION")
print("=" * 70)

# Test URLs (mix of formats)
test_urls = [
    {
        'name': 'OpenAPI Spec (Petstore)',
        'url': 'https://raw.githubusercontent.com/OAI/OpenAPI-Specification/main/examples/v3.0/petstore.yaml'
    },
    {
        'name': 'Stripe API Docs (HTML)',
        'url': 'https://stripe.com/docs/api/customers'
    },
    {
        'name': 'GitHub API Docs (HTML)',
        'url': 'https://docs.github.com/en/rest/users'
    }
]

extractor = APIExtractor()

for test in test_urls:
    print(f"\n{'='*70}")
    print(f"Testing: {test['name']}")
    print(f"URL: {test['url']}")
    print('='*70)
    
    result = extractor.extract_from_url(test['url'])
    
    if result['success']:
        print(f"✅ Success! Method: {result['method']}")
        
        data = result['data']
        
        if result['method'] == 'openapi':
            print(f"API: {data['info']['title']}")
            print(f"Endpoints: {len(data['endpoints'])}")
            print(f"Schemas: {len(data['schemas'])}")
        else:
            print(f"API: {data.get('api_info', {}).get('name', 'Unknown')}")
            print(f"Endpoints: {len(data.get('endpoints', []))}")
            print(f"Schemas: {len(data.get('schemas', {}))}")
            print(f"Needs more pages: {data.get('needs_more_pages', False)}")
            
            if data.get('endpoints'):
                print("\nFirst endpoint:")
                ep = data['endpoints'][0]
                print(f"  {ep.get('method')} {ep.get('path')}")
                print(f"  {ep.get('description', 'No description')}")
        
        print(f"\n📄 Full JSON (truncated):")
        print(json.dumps(data, indent=2)[:500] + "...")
    else:
        print(f"❌ Failed: {result['error']}")
    
    print("\n" + "="*70)

print("\n✅ Single-page extraction testing complete!")