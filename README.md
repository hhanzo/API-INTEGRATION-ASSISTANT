# API Integration Assistant

Automatically analyze two API documentation sources and generate OpenAPI 3.1.0 specs.

## Setup
```bash
pip install -r requirements.txt
```

## Run
```bash
streamlit run app.py
```

## Features
- **Dual URL extraction workflow**: The Streamlit UI accepts **API A** and **API B** documentation URLs and processes both in one run.
- **Hybrid extraction strategy**: Each URL is first checked as a raw OpenAPI/Swagger spec, then falls back to crawler + LLM extraction for HTML documentation pages.
- **OpenAPI 3.1 generation**: Extracted data is normalized into OpenAPI **3.1.0** output.
- **Built-in validation status**: Generated specs are validated and shown with pass/fail status and validation error details.
- **Download options**: Export each generated API spec as **JSON** or **YAML**, plus an optional combined JSON bundle.

## Architecture (Module Map)
- `app.py`
  - Streamlit entrypoint and UI orchestration.
  - Collects API A/API B URLs, runs extraction, builds specs, validates output, and renders previews/downloads.
- `crawler.py`
  - Multi-page crawl coordinator (`APICrawler`).
  - Tracks visited pages, merges extracted endpoint/schema/auth data, and supports progress callbacks.
- `extractor.py`
  - Single-page extraction strategy (`APIExtractor`).
  - Attempts direct OpenAPI parsing first; if unavailable, uses HTML scraping + LLM-driven structured extraction.
- `openapi_builder.py`
  - Converts normalized extraction data into OpenAPI 3.1.0 documents.
  - Includes validation helpers used by the UI to show validity and errors.

## Configuration Prerequisites (LLM Flows)
LLM-assisted extraction is still used for non-OpenAPI documentation pages.

1. Create a `.env` file in the project root.
2. Add your Gemini key:
   ```bash
   GEMINI_API_KEY=your_key_here
   ```
3. Restart the app/session after updating environment variables.

If `GEMINI_API_KEY` is missing, LLM-based extraction paths will fail to initialize.


## Dependency Management
### Runtime dependencies (`requirements.txt`)
The runtime dependency set is pinned and aligned to imports used by the app:
- `streamlit`, `requests`, `pyyaml`
- `python-dotenv`, `google-generativeai`
- `beautifulsoup4`, `lxml`, `readability-lxml`

### Dependency audit notes
- Removed `anthropic` and `openai`: no active imports or usage in the current codebase.
- Removed `jsonschema`: OpenAPI validation is currently implemented with project-local checks in `openapi_builder.py`, not the `jsonschema` package.
- Kept `lxml`: used as the BeautifulSoup parser backend (`BeautifulSoup(..., "lxml")`) in the scraper pipeline.

### Development dependencies (`requirements-dev.txt`)
Development and test tooling is isolated in `requirements-dev.txt` so runtime installs stay minimal while local lint/format/test workflows remain reproducible.

## Testing
### Automated / scripted checks
This repo currently includes script-style checks (not a formal `pytest` suite). Common files:
- `test_fetch.py`
- `test_openapi.py`
- `test_extractor.py`
- `test_mapping.py`
- `test_gemini.py`

Run any script directly, for example:
```bash
python test_extractor.py
```

### Optional manual validation
Use the app UI for end-to-end checks:
1. Run `streamlit run app.py`.
2. Enter two documentation URLs (OpenAPI URLs and/or HTML docs).
3. Confirm path/schema counts, validation status, and JSON/YAML download behavior.
