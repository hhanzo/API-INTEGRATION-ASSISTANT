from openapi_builder import build_openapi_spec
import json 


test_json = '/Users/sabharish/Documents/Python/Python Practice/api-integration-assistant/api_a_extracted.json'
spec  = build_openapi_spec(json.load(open(test_json)))

with open("openapi_spec.json", "w") as f:
    json.dump(spec, f, indent=2)