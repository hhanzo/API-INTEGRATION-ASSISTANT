# API Integration Assistant

Automatically analyze two API documentation sources and generate OpenAPI 3.1.0 specs.

## Phase 0 Design Lock (Current → End Goal)

This project is transitioning from an **API extraction tool** into a full **integration planning assistant**.

### End goal pipeline
1. **Extract APIs** from documentation/spec URLs
2. **Map entities and fields** between API A and API B
3. **Ask user integration questions** (direction, ownership, retry/error policy, conflict rules, etc.)
4. **Generate final integration plan** as machine-readable + human-readable artifacts

### Current state (today)
- ✅ Extraction + OpenAPI generation implemented
- ⚠️ Mapping exists as prompt/test prototype, not integrated in app flow
- ❌ User questionnaire stage not implemented
- ❌ Final integration plan generation not implemented

### Target artifacts (canonical pipeline outputs)
The pipeline should produce and pass forward these artifacts:

1. `extracted_api_a` / `extracted_api_b`
   - OpenAPI output + normalized entities/operations/auth metadata
2. `mapping_result`
   - Entity mappings + field mappings + confidence + transformation notes
3. `integration_answers`
   - Structured user decisions from guided questionnaire
4. `integration_plan`
   - Final flow design including transformations, errors/retries, auth, ownership, risks, and implementation backlog

---

## MVP Acceptance Criteria (Definition of Done)

The MVP is considered complete when all items below are true:

1. User provides API A + API B URLs in the app.
2. App extracts both APIs and produces valid OpenAPI output for each.
3. App generates and displays entity/field mapping candidates with confidence levels.
4. App collects required integration decisions through a guided questionnaire.
5. App generates a deterministic integration plan from extraction + mapping + answers.
6. App allows download/export of:
   - integration plan JSON
   - integration plan Markdown summary
7. App handles partial/low-confidence mapping cases with visible warnings (no hard crash).

### Non-goals for MVP
- Full production-grade orchestration/runtime execution engine
- Auto-deployment of integration pipelines
- Fully autonomous planning without user confirmation for ambiguous mappings

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

## Planned Next Stages (Post Phase 0)
- Mapping stage integrated directly into app workflow (not test script only)
- Questionnaire UI with required integration decisions
- Deterministic integration plan generator and exports (JSON + Markdown)
- End-to-end tests for extraction → mapping → Q&A → plan output

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
