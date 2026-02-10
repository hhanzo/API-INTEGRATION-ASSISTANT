def build_openapi_spec(extracted: dict) -> dict:

    info = extracted.get("api_info", {}) or {}

    spec = {
        "openapi": "3.1.0",
        "jsonSchemaDialect": "https://json-schema.org/draft/2020-12/schema",
        "info": {
            "title": info.get("name") or "Extracted API",
            "description": info.get("description") or "",
            "version": info.get("version") or "1.0.0"
        },
        "servers": [],
        "paths": {},
        "components": {
            "schemas": {}
        }
    }

    base_url = info.get("base_url")
    if base_url:
        spec["servers"].append({"url": base_url})

    for ep in extracted.get("endpoints", []):

        path = ep["path"]
        method = ep["method"].lower()

        if path not in spec["paths"]:
            spec["paths"][path] = {}

        operation = {
            "summary": ep.get("description", ""),
            "responses": {}
        }

        # --------------------
        # Parameters
        # --------------------
        parameters = []
        request_body = None

        request = ep.get("request") or {}

        for p in request.get("parameters", []):

            if p["location"] == "body":
                continue

            parameters.append({
                "name": p["name"],
                "in": p["location"],
                "required": p.get("required", False),
                "description": p.get("description", ""),
                "schema": {
                    "type": p.get("type", "string")
                },
                "example": p.get("example")
            })

        if parameters:
            operation["parameters"] = parameters

        # --------------------
        # Request body
        # --------------------
        body_schema = request.get("schema")

        if body_schema:
            request_body = {
                "required": True,
                "content": {
                    request.get("content_type", "application/json"): {
                        "schema": body_schema,
                        "example": request.get("example")
                    }
                }
            }

            operation["requestBody"] = request_body

        # --------------------
        # Responses
        # --------------------
        for status, resp in (ep.get("responses") or {}).items():

            content = None
            schema = resp.get("schema")

            if schema:
                content = {
                    resp.get("content_type", "application/json"): {
                        "schema": schema,
                        "example": resp.get("example")
                    }
                }

            operation["responses"][str(status)] = {
                "description": resp.get("description", ""),
                **({"content": content} if content else {})
            }

        spec["paths"][path][method] = operation

    # --------------------
    # Common schemas
    # --------------------
    for name, schema in (extracted.get("common_schemas") or {}).items():
        spec["components"]["schemas"][name] = schema

    return spec


def _convert_object_schema(fields: dict) -> dict:
    """
    Converts your light-weight field schema into OpenAPI schema.
    """

    properties = {}
    required = []

    for name, f in fields.items():
        properties[name] = {
            "type": f.get("type", "string"),
            "description": f.get("description", "")
        }

        if "example" in f:
            properties[name]["example"] = f["example"]

        if f.get("required"):
            required.append(name)

    schema = {
        "type": "object",
        "properties": properties
    }

    if required:
        schema["required"] = required

    return schema
