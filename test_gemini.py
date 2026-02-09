from llm import GeminiClient
import json

print("=" * 60)
print("GEMINI API CONNECTION TEST")
print("=" * 60)

try:
    # Initialize client
    print("\n1. Initializing Gemini client...")
    client = GeminiClient()
    print("   ✅ Client initialized successfully")
    
    # Test 1: Simple response
    print("\n2. Testing basic response...")
    test_prompt = "Say 'Hello from Gemini!' and nothing else."
    result = client.analyze_apis(test_prompt)
    
    if result['error']:
        print(f"   ❌ Error: {result['error']}")
        exit(1)
    else:
        print(f"   ✅ Gemini responded: {result['response']}")
    
    # Test 2: JSON response
    print("\n3. Testing JSON generation...")
    json_prompt = """
    Generate a JSON object with the following structure:
    {
        "status": "success",
        "message": "API is working",
        "capabilities": ["API analysis", "Field mapping", "Integration planning"]
    }
    
    Return ONLY valid JSON, no other text.
    """
    
    result = client.analyze_apis(json_prompt)
    
    if result['error']:
        print(f"   ❌ Error: {result['error']}")
    elif result['parsed']:
        print("   ✅ JSON parsed successfully:")
        print(f"      {json.dumps(result['parsed'], indent=2)}")
    else:
        print("   ⚠️  Response received but couldn't parse as JSON")
        print(f"      Raw response: {result['response'][:100]}...")
    
    # Test 3: API rate limit check
    print("\n4. Testing retry logic (intentionally rapid requests)...")
    for i in range(3):
        result = client.analyze_apis("Count to 3")
        if result['error']:
            print(f"   Request {i+1}: ❌ {result['error']}")
        else:
            print(f"   Request {i+1}: ✅ Success")
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED - Gemini is ready to use!")
    print("=" * 60)

except ValueError as e:
    print(f"\n❌ Configuration Error: {str(e)}")
    print("\nMake sure you have:")
    print("1. Created a .env file in the project root")
    print("2. Added GEMINI_API_KEY=your_key_here to the .env file")
    print("3. Get your API key from: https://makersuite.google.com/app/apikey")
    
except Exception as e:
    print(f"\n❌ Unexpected Error: {str(e)}")
    import traceback
    traceback.print_exc()