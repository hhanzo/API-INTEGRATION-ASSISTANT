# API Integration Assistant

Automatically analyze two API documentation sources and generate OpenAPI 3.1.0 specs.

## Project Status (Current)

The application now supports the full guided flow:
- Extract API A and API B specs from docs/spec URLs
- Generate entity/field mappings with confidence and transformation hints
- Collect validated integration decisions through a questionnaire
- Generate deterministic integration plans and export JSON/Markdown artifacts

Core automated tests for contracts, mapper, questionnaire, plan generation, and end-to-end flow are in place.


### End goal pipeline
1. **Extract APIs** from documentation/spec URLs
2. **Map entities and fields** between API A and API B
3. **Ask user integration questions** (direction, ownership, retry/error policy, conflict rules, etc.)
4. **Generate final integration plan** as machine-readable + human-readable artifacts

### Current state (today)
- ✅ Extraction + OpenAPI generation implemented
- ✅ Mapping stage integrated in app flow
- ✅ Guided questionnaire implemented and validated
- ✅ Deterministic integration plan generation implemented (JSON + Markdown export)

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
- **Hybrid extraction strategy**: Each URL is first checked as a raw OpenAPI/Swagger spec, then falls back to scraper + LLM extraction for HTML documentation pages.
- **OpenAPI 3.1 generation**: Extracted data is normalized into OpenAPI **3.1.0** output.
- **Mapping generation stage**: Entity and field mappings are generated with confidence levels and transformation notes.
- **Guided questionnaire stage**: Integration decisions (direction, trigger mode, conflict/error strategy, retry policy, ownership, etc.) are collected and validated.
- **Integration plan generation stage**: Deterministic plan synthesis with contract validation, plus exports to JSON and Markdown.
- **Download options**:
  - API A OpenAPI (JSON/YAML)
  - API B OpenAPI (JSON/YAML)
  - Combined API bundle JSON
  - Mapping result JSON
  - Integration answers JSON
  - Integration plan JSON + Markdown

## End-to-End App Workflow
1. **Extract** API A and API B docs/spec URLs.
2. **Review OpenAPI outputs** and validation status.
3. **Generate mappings** and inspect confidence/warnings.
4. **Save integration answers** from the guided questionnaire.
5. **Generate integration plan** and export artifacts.

## Output Artifacts
- `openapi_a` / `openapi_b`
- `mapping_result`
- `integration_answers`
- `integration_plan`

## Architecture (Module Map)
- `app.py`
  - Streamlit entrypoint and UI orchestration.
  - Executes extraction → mapping → questionnaire → integration plan flow.
- `crawler.py`
  - Multi-page crawl coordinator (`APICrawler`).
  - Tracks visited pages, merges extracted endpoint/schema/auth data, and supports progress callbacks.
- `extractor.py`
  - Single-page extraction strategy (`APIExtractor`).
  - Attempts direct OpenAPI parsing first; if unavailable, uses HTML scraping + LLM-driven structured extraction.
- `openapi_builder.py`
  - Converts normalized extraction data into OpenAPI 3.1.0 documents.
  - Includes validation helpers used by the UI to show validity and errors.
- `mapper.py`
  - Mapping runtime service.
  - Normalizes OpenAPI schema views, builds mapping prompts, validates mapping output against contract.
- `questionnaire.py`
  - Questionnaire defaults, options, and validation helpers.
- `plan_generator.py`
  - Deterministic integration plan builder + Markdown renderer.
- `contracts.py`
  - Canonical validation helpers for mapping, questionnaire answers, and integration plan artifacts.

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
### Pytest suite (recommended)
The core pipeline modules are covered by assertion-based tests:
- `test_contracts.py`
- `test_mapper.py`
- `test_questionnaire.py`
- `test_plan_generator.py`
- `test_end_to_end_flow.py`

Run them with:
```bash
python3 -m pytest -q test_contracts.py test_mapper.py test_questionnaire.py test_plan_generator.py test_end_to_end_flow.py
```

### Legacy script-style checks
Some exploratory script tests still exist (`test_fetch.py`, `test_gemini.py`, `test_extractor.py`, `test_openapi.py`) and can be run manually if needed.

### Optional manual validation
Use the app UI for end-to-end checks:
1. Run `streamlit run app.py`.
2. Enter two documentation URLs (OpenAPI URLs and/or HTML docs).
3. Run mapping generation and inspect confidence/warnings.
4. Save integration answers.
5. Generate integration plan and verify JSON/Markdown exports.

## Current Limitations / Notes
- Mapping quality depends on extracted schema quality and LLM output quality.
- Low-confidence mappings still require human review before production usage.
- The LLM SDK used in `llm.py` (`google.generativeai`) emits a deprecation warning; migration to `google.genai` is recommended.
- Crawler module exists, but the current app flow is centered on single-page extraction + mapping/planning stages.
- Some JS-heavy documentation pages (for example GitHub REST docs pages) can be intermittently less reliable than direct OpenAPI URLs due to HTML noise and LLM extraction variability.
