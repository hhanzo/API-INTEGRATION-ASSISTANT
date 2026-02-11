import streamlit as st
from extractor import APIExtractor
from openapi_builder import build_openapi_spec, validate_openapi_spec
from mapper import generate_mappings
from plan_generator import generate_integration_plan, render_integration_plan_markdown
from questionnaire import (
    merge_with_defaults,
    questionnaire_option_sets,
    validate_questionnaire_answers,
)
import json
import yaml

st.set_page_config(
    page_title="API Integration Assistant",
    page_icon="🔗",
    layout="wide"
)

st.title("🔗 Universal API Integration Assistant")
st.markdown("Extract API specs from **any** documentation and generate **OpenAPI 3.1.0** specifications.")


def _render_mapping_results(mapping_result: dict) -> None:
    """Render entity and field mappings in the app."""
    entity_mappings = mapping_result.get("entity_mappings", [])
    warnings = mapping_result.get("warnings", [])

    if warnings:
        st.warning("⚠️ Mapping warnings detected:")
        for warning in warnings:
            st.write(f"- {warning}")

    if not entity_mappings:
        st.info("No entity mappings were identified yet.")
        return

    st.success(
        f"Found {len(entity_mappings)} entity mapping(s) with "
        f"{sum(len(m.get('field_mappings', [])) for m in entity_mappings)} field mapping(s)."
    )

    for idx, entity_map in enumerate(entity_mappings, start=1):
        api_a_entity = entity_map.get("api_a_entity", "Unknown")
        api_b_entity = entity_map.get("api_b_entity", "Unknown")
        confidence = entity_map.get("confidence", "UNKNOWN")
        reasoning = entity_map.get("reasoning", "")

        with st.expander(
            f"{idx}. {api_a_entity} → {api_b_entity} ({confidence})",
            expanded=(idx == 1),
        ):
            if reasoning:
                st.caption(reasoning)

            field_rows = []
            for field_map in entity_map.get("field_mappings", []):
                transformation = field_map.get("transformation")
                if isinstance(transformation, dict):
                    transformation_value = json.dumps(transformation)
                else:
                    transformation_value = transformation if transformation is not None else ""

                field_rows.append(
                    {
                        "API A Field": field_map.get("api_a_field", ""),
                        "API B Field": field_map.get("api_b_field", ""),
                        "Confidence": field_map.get("confidence", ""),
                        "Transformation": transformation_value,
                        "Notes": field_map.get("notes", ""),
                    }
                )

            if field_rows:
                st.dataframe(field_rows, use_container_width=True)
            else:
                st.info("No field-level mappings provided for this entity pair.")

    unmapped_a = mapping_result.get("unmapped_entities_a", [])
    unmapped_b = mapping_result.get("unmapped_entities_b", [])
    if unmapped_a or unmapped_b:
        col_unmapped_a, col_unmapped_b = st.columns(2)
        with col_unmapped_a:
            st.write("**Unmapped Entities in API A**")
            if unmapped_a:
                for item in unmapped_a:
                    st.write(f"- {item}")
            else:
                st.caption("None")
        with col_unmapped_b:
            st.write("**Unmapped Entities in API B**")
            if unmapped_b:
                for item in unmapped_b:
                    st.write(f"- {item}")
            else:
                st.caption("None")


def _render_questionnaire_section() -> None:
    """Render guided integration questionnaire and persist answers."""
    st.divider()
    st.header("🧩 Integration Decisions Questionnaire")
    st.caption("Capture business and technical integration decisions required for final planning.")

    option_sets = questionnaire_option_sets()
    defaults = merge_with_defaults(st.session_state.get("integration_answers"))

    with st.form("integration_questionnaire_form"):
        col_q1, col_q2 = st.columns(2)

        with col_q1:
            goal = st.selectbox("Integration goal", option_sets["goal"], index=option_sets["goal"].index(defaults["goal"]))
            source_of_truth = st.selectbox(
                "Source of truth",
                option_sets["source_of_truth"],
                index=option_sets["source_of_truth"].index(defaults["source_of_truth"]),
            )
            sync_direction = st.selectbox(
                "Sync direction",
                option_sets["sync_direction"],
                index=option_sets["sync_direction"].index(defaults["sync_direction"]),
            )
            trigger_mode = st.selectbox(
                "Trigger mode",
                option_sets["trigger_mode"],
                index=option_sets["trigger_mode"].index(defaults["trigger_mode"]),
            )
            latency_slo = st.selectbox(
                "Latency target",
                option_sets["latency_slo"],
                index=option_sets["latency_slo"].index(defaults["latency_slo"]),
            )

        with col_q2:
            conflict_strategy = st.selectbox(
                "Conflict strategy",
                option_sets["conflict_strategy"],
                index=option_sets["conflict_strategy"].index(defaults["conflict_strategy"]),
            )
            error_strategy = st.selectbox(
                "Error strategy",
                option_sets["error_strategy"],
                index=option_sets["error_strategy"].index(defaults["error_strategy"]),
            )
            pii_handling = st.selectbox(
                "PII handling",
                option_sets["pii_handling"],
                index=option_sets["pii_handling"].index(defaults["pii_handling"]),
            )
            idempotency = st.checkbox("Require idempotency", value=bool(defaults["idempotency"]))
            max_retries = st.number_input(
                "Max retries",
                min_value=0,
                max_value=20,
                value=int(defaults.get("retry_policy", {}).get("max_retries", 3)),
                step=1,
            )
            backoff = st.selectbox(
                "Retry backoff",
                option_sets["backoff"],
                index=option_sets["backoff"].index(defaults.get("retry_policy", {}).get("backoff", "exponential")),
            )

        ownership_notes = st.text_area(
            "Ownership notes (required)",
            value=defaults.get("ownership_notes", ""),
            placeholder="e.g., Platform team owns mapping rules and on-call support",
            height=90,
        )

        save_questionnaire = st.form_submit_button("💾 Save Integration Answers", use_container_width=True)

    if save_questionnaire:
        answers = {
            "goal": goal,
            "source_of_truth": source_of_truth,
            "sync_direction": sync_direction,
            "trigger_mode": trigger_mode,
            "latency_slo": latency_slo,
            "conflict_strategy": conflict_strategy,
            "error_strategy": error_strategy,
            "retry_policy": {"max_retries": int(max_retries), "backoff": backoff},
            "idempotency": bool(idempotency),
            "pii_handling": pii_handling,
            "ownership_notes": ownership_notes,
        }

        is_valid, errors = validate_questionnaire_answers(answers)
        if is_valid:
            st.session_state["integration_answers"] = merge_with_defaults(answers)
            st.success("✅ Integration answers saved")
        else:
            st.error("❌ Please fix questionnaire validation issues:")
            for error in errors:
                st.write(f"- {error}")

    if "integration_answers" in st.session_state:
        st.subheader("📌 Saved Integration Answers")
        st.code(json.dumps(st.session_state["integration_answers"], indent=2), language="json")
        st.download_button(
            label="📥 Download Integration Answers (JSON)",
            data=json.dumps(st.session_state["integration_answers"], indent=2),
            file_name="integration_answers.json",
            mime="application/json",
            use_container_width=True,
        )


def _render_plan_generation_section(openapi_a: dict, openapi_b: dict) -> None:
    """Render Phase 5 plan generation controls and outputs."""
    st.divider()
    st.header("🗺️ Integration Plan")
    st.caption("Generate a deterministic integration plan from mappings and saved answers.")

    if st.button("🛠️ Generate Integration Plan", type="primary", use_container_width=True):
        mapping_result = st.session_state.get("mapping_result", {})
        answers = st.session_state.get("integration_answers", {})

        with st.spinner("Generating integration plan..."):
            plan_outcome = generate_integration_plan(
                openapi_a=openapi_a,
                openapi_b=openapi_b,
                mapping_result=mapping_result,
                integration_answers=answers,
            )

        st.session_state["integration_plan"] = plan_outcome.get("data", {})
        st.session_state["integration_plan_error"] = plan_outcome.get("error")
        st.session_state["integration_plan_validation_errors"] = plan_outcome.get(
            "validation_errors", []
        )

        if plan_outcome.get("success"):
            st.success("✅ Integration plan generated")
        else:
            st.error("❌ Integration plan generated with validation fallback")

    if "integration_plan" in st.session_state:
        plan = st.session_state["integration_plan"]
        plan_error = st.session_state.get("integration_plan_error")
        validation_errors = st.session_state.get("integration_plan_validation_errors", [])

        if plan_error:
            st.caption(f"Plan generation note: {plan_error}")
        if validation_errors:
            st.warning("Validation issues detected while building the plan:")
            for err in validation_errors:
                st.write(f"- {err}")

        with st.expander("👁️ Preview Integration Plan (JSON)", expanded=True):
            st.code(json.dumps(plan, indent=2), language="json")

        markdown_plan = render_integration_plan_markdown(plan)
        with st.expander("📝 Preview Integration Plan (Markdown)"):
            st.markdown(markdown_plan)

        col_export_json, col_export_md = st.columns(2)
        with col_export_json:
            st.download_button(
                label="📥 Download Integration Plan (JSON)",
                data=json.dumps(plan, indent=2),
                file_name="integration_plan.json",
                mime="application/json",
                use_container_width=True,
            )
        with col_export_md:
            st.download_button(
                label="📥 Download Integration Plan (Markdown)",
                data=markdown_plan,
                file_name="integration_plan.md",
                mime="text/markdown",
                use_container_width=True,
            )

# Sidebar settings
with st.sidebar:
    st.header("⚙️ Extraction Settings")
    max_pages = st.slider("Max pages to crawl", 1, 20, 5)
    crawl_delay = st.slider("Delay between requests (seconds)", 0.5, 3.0, 1.0)
    
    st.divider()
    st.header("📥 Output Format")
    output_format = st.radio("OpenAPI format", ["JSON", "YAML"], index=0)
    
    st.info("**Tip:** Start with 5 pages. Increase if documentation is spread across many pages.")

# Input section
col1, col2 = st.columns(2)

with col1:
    st.subheader("🌐 API A Documentation")
    api_a_url = st.text_input(
        "Enter documentation URL",
        value="https://stripe.com/docs/api/customers",
        placeholder="https://stripe.com/docs/api/customers",
        help="Can be OpenAPI spec URL or any documentation page",
        key="api_a"
    )

with col2:
    st.subheader("🌐 API B Documentation")
    api_b_url = st.text_input(
        "Enter documentation URL",
        value="https://docs.github.com/en/rest/users?apiVersion=2022-11-28",
        placeholder="https://docs.github.com/en/rest/users",
        help="Can be OpenAPI spec URL or any documentation page",
        key="api_b"
    )

# Main analyze button
st.divider()

if st.button("🚀 Extract APIs to OpenAPI 3.1.0", type="primary", use_container_width=True):
    if not api_a_url or not api_b_url:
        st.error("Please provide both API documentation URLs")
    else:
        # Progress containers
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Initialize holders
        openapi_a = openapi_b = None
        is_valid_a = is_valid_b = False
        errors_a = []
        errors_b = []
        meta_a = {}
        meta_b = {}

        # Extract API A
        status_text.text("🧠 Analyzing API A documentation...")
        progress_bar.progress(10)

        extractor_a = APIExtractor()
        result_a = extractor_a.extract_from_url(api_a_url)

        if not result_a.get("success"):
            st.error(f"API A extraction failed: {result_a.get('error', 'Unknown error')}")
        else:
            extracted_a = result_a.get("data") or {}
            # Fallback: ensure source_url is present for builders and UI
            api_info_a = extracted_a.get("api_info", {})
            if not api_info_a.get("source_url"):
                api_info_a["source_url"] = api_a_url
                extracted_a["api_info"] = api_info_a

            meta_a = {
                "method": result_a.get("method"),
                "doc_type": result_a.get("doc_type"),
                "needs_more_pages": bool(extracted_a.get("needs_more_pages")),
                "suggested_urls": extracted_a.get("suggested_urls") or [],
            }

            # Build OpenAPI spec for A
            status_text.text("🔨 Building OpenAPI spec for API A...")
            progress_bar.progress(40)
            openapi_a = build_openapi_spec(extracted_a)

            # Validate
            status_text.text("✅ Validating OpenAPI spec for API A...")
            is_valid_a, errors_a = validate_openapi_spec(openapi_a)

        # Extract API B
        status_text.text("🧠 Analyzing API B documentation...")
        progress_bar.progress(55)

        extractor_b = APIExtractor()
        result_b = extractor_b.extract_from_url(api_b_url)

        if not result_b.get("success"):
            st.error(f"API B extraction failed: {result_b.get('error', 'Unknown error')}")
        else:
            extracted_b = result_b.get("data") or {}
            # Fallback: ensure source_url is present for builders and UI
            api_info_b = extracted_b.get("api_info", {})
            if not api_info_b.get("source_url"):
                api_info_b["source_url"] = api_b_url
                extracted_b["api_info"] = api_info_b

            meta_b = {
                "method": result_b.get("method"),
                "doc_type": result_b.get("doc_type"),
                "needs_more_pages": bool(extracted_b.get("needs_more_pages")),
                "suggested_urls": extracted_b.get("suggested_urls") or [],
            }

            # Build OpenAPI spec for B
            status_text.text("🔨 Building OpenAPI spec for API B...")
            progress_bar.progress(80)
            openapi_b = build_openapi_spec(extracted_b)

            # Validate
            status_text.text("✅ Validating OpenAPI spec for API B...")
            is_valid_b, errors_b = validate_openapi_spec(openapi_b)

        # Finalize progress
        progress_bar.progress(100)
        status_text.text("✅ Extraction complete!")

        # Store in session state if both APIs were successfully built
        if openapi_a is not None and openapi_b is not None:
            st.session_state['openapi_a'] = openapi_a
            st.session_state['openapi_b'] = openapi_b
            st.session_state['is_valid_a'] = is_valid_a
            st.session_state['is_valid_b'] = is_valid_b
            st.session_state['errors_a'] = errors_a
            st.session_state['errors_b'] = errors_b
            st.session_state['meta_a'] = meta_a
            st.session_state['meta_b'] = meta_b
            # Reset downstream stages when extraction is re-run
            st.session_state.pop('mapping_result', None)
            st.session_state.pop('mapping_error', None)
            st.session_state.pop('mapping_raw_response', None)

            # Success message
            st.success(f"""
            ✅ **Extraction Complete!**
            - API A: {len(openapi_a.get('paths', {}))} paths, {len(openapi_a.get('components', {}).get('schemas', {}))} schemas
            - API B: {len(openapi_b.get('paths', {}))} paths, {len(openapi_b.get('components', {}).get('schemas', {}))} schemas
            """)

            if not is_valid_a or not is_valid_b:
                st.warning("⚠️ Some validation warnings detected. See details below.")

            st.balloons()

# Display results
if 'openapi_a' in st.session_state and 'openapi_b' in st.session_state:
    st.divider()
    st.header("📊 OpenAPI 3.1.0 Specifications")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🔵 API A")
        openapi_a = st.session_state['openapi_a']
        is_valid_a = st.session_state['is_valid_a']
        meta_a = st.session_state.get('meta_a', {})

        # Source / extraction metadata
        method_a = meta_a.get("method")
        doc_type_a = meta_a.get("doc_type")
        if method_a == "openapi":
            st.caption("Source: OpenAPI/Swagger specification URL")
        elif method_a == "llm_extraction":
            doc_label_a = doc_type_a or "unknown"
            st.caption(f"Source: Scraped documentation + LLM extraction ({doc_label_a} style)")
        elif method_a:
            st.caption(f"Source method: {method_a}")

        if meta_a.get("needs_more_pages"):
            suggested_a = meta_a.get("suggested_urls") or []
            if suggested_a:
                st.caption("Additional suggested documentation pages detected:")
                for s_url in suggested_a[:3]:
                    st.write(f"- {s_url}")
        
        # Validation status
        if is_valid_a:
            st.success("✅ Valid OpenAPI 3.1.0 Specification")
        else:
            st.error("❌ Validation errors:")
            for error in st.session_state['errors_a']:
                st.write(f"  - {error}")
        
        # Metrics
        col_a1, col_a2, col_a3 = st.columns(3)
        with col_a1:
            st.metric("Paths", len(openapi_a.get('paths', {})))
        with col_a2:
            st.metric("Schemas", len(openapi_a.get('components', {}).get('schemas', {})))
        with col_a3:
            st.metric("Version", openapi_a.get('openapi', 'unknown'))
        
        # Info
        st.write(f"**Title:** {openapi_a.get('info', {}).get('title', 'N/A')}")
        st.write(f"**Version:** {openapi_a.get('info', {}).get('version', 'N/A')}")
        
        # Preview
        with st.expander("👁️ Preview OpenAPI Spec (first 50 lines)"):
            if output_format == "JSON":
                preview = json.dumps(openapi_a, indent=2)
            else:
                preview = yaml.dump(openapi_a, default_flow_style=False, sort_keys=False)
            st.code(preview.split('\n')[:50], language='yaml' if output_format == 'YAML' else 'json')
        
        # Download button
        st.divider()
        if output_format == "JSON":
            file_content = json.dumps(openapi_a, indent=2)
            file_name = "api_a_openapi.json"
            mime_type = "application/json"
        else:
            file_content = yaml.dump(openapi_a, default_flow_style=False, sort_keys=False)
            file_name = "api_a_openapi.yaml"
            mime_type = "text/yaml"
        
        st.download_button(
            label=f"📥 Download API A OpenAPI Spec ({output_format})",
            data=file_content,
            file_name=file_name,
            mime=mime_type,
            use_container_width=True
        )
    
    with col2:
        st.subheader("🟢 API B")
        openapi_b = st.session_state['openapi_b']
        is_valid_b = st.session_state['is_valid_b']
        meta_b = st.session_state.get('meta_b', {})

        # Source / extraction metadata
        method_b = meta_b.get("method")
        doc_type_b = meta_b.get("doc_type")
        if method_b == "openapi":
            st.caption("Source: OpenAPI/Swagger specification URL")
        elif method_b == "llm_extraction":
            doc_label_b = doc_type_b or "unknown"
            st.caption(f"Source: Scraped documentation + LLM extraction ({doc_label_b} style)")
        elif method_b:
            st.caption(f"Source method: {method_b}")

        if meta_b.get("needs_more_pages"):
            suggested_b = meta_b.get("suggested_urls") or []
            if suggested_b:
                st.caption("Additional suggested documentation pages detected:")
                for s_url in suggested_b[:3]:
                    st.write(f"- {s_url}")
        
        # Validation status
        if is_valid_b:
            st.success("✅ Valid OpenAPI 3.1.0 Specification")
        else:
            st.error("❌ Validation errors:")
            for error in st.session_state['errors_b']:
                st.write(f"  - {error}")
        
        # Metrics
        col_b1, col_b2, col_b3 = st.columns(3)
        with col_b1:
            st.metric("Paths", len(openapi_b.get('paths', {})))
        with col_b2:
            st.metric("Schemas", len(openapi_b.get('components', {}).get('schemas', {})))
        with col_b3:
            st.metric("Version", openapi_b.get('openapi', 'unknown'))
        
        # Info
        st.write(f"**Title:** {openapi_b.get('info', {}).get('title', 'N/A')}")
        st.write(f"**Version:** {openapi_b.get('info', {}).get('version', 'N/A')}")
        
        # Preview
        with st.expander("👁️ Preview OpenAPI Spec (first 50 lines)"):
            if output_format == "JSON":
                preview = json.dumps(openapi_b, indent=2)
            else:
                preview = yaml.dump(openapi_b, default_flow_style=False, sort_keys=False)
            st.code(preview.split('\n')[:50], language='yaml' if output_format == 'YAML' else 'json')
        
        # Download button
        st.divider()
        if output_format == "JSON":
            file_content = json.dumps(openapi_b, indent=2)
            file_name = "api_b_openapi.json"
            mime_type = "application/json"
        else:
            file_content = yaml.dump(openapi_b, default_flow_style=False, sort_keys=False)
            file_name = "api_b_openapi.yaml"
            mime_type = "text/yaml"
        
        st.download_button(
            label=f"📥 Download API B OpenAPI Spec ({output_format})",
            data=file_content,
            file_name=file_name,
            mime=mime_type,
            use_container_width=True
        )
    
    # Combined download
    st.divider()
    st.subheader("📦 Download Both APIs")
    
    col_download1, col_download2 = st.columns(2)
    
    with col_download1:
        # Combined JSON
        combined = {
            "api_a": openapi_a,
            "api_b": openapi_b
        }
        st.download_button(
            label="📥 Download Both as JSON Bundle",
            data=json.dumps(combined, indent=2),
            file_name="both_apis_bundle.json",
            mime="application/json",
            use_container_width=True
        )
    
    with col_download2:
        # ZIP file would require additional library
        st.info("💡 Download each API separately above")

    # Mapping stage
    st.divider()
    st.header("🧭 Entity & Field Mapping")
    st.caption(
        "Generate mapping candidates between API A and API B using the extracted OpenAPI specs."
    )

    if st.button("🧠 Generate Field Mappings", type="secondary", use_container_width=True):
        with st.spinner("Generating mappings..."):
            mapping_outcome = generate_mappings(openapi_a, openapi_b)

        st.session_state['mapping_result'] = mapping_outcome.get('data', {})
        st.session_state['mapping_error'] = mapping_outcome.get('error')
        st.session_state['mapping_raw_response'] = mapping_outcome.get('raw_response')

        if mapping_outcome.get('success'):
            st.success("✅ Mapping generation complete")
        else:
            st.error(
                "❌ Mapping generation had issues. Showing fallback output with warnings."
            )

    if 'mapping_result' in st.session_state:
        mapping_error = st.session_state.get('mapping_error')
        if mapping_error:
            st.caption(f"Last mapping error: {mapping_error}")

        _render_mapping_results(st.session_state['mapping_result'])

        with st.expander("👁️ Preview Raw Mapping JSON"):
            st.code(
                json.dumps(st.session_state['mapping_result'], indent=2),
                language='json',
            )

        st.download_button(
            label="📥 Download Mapping Result (JSON)",
            data=json.dumps(st.session_state['mapping_result'], indent=2),
            file_name="api_mapping_result.json",
            mime="application/json",
            use_container_width=True,
        )

        _render_questionnaire_section()

        if "integration_answers" in st.session_state:
            _render_plan_generation_section(openapi_a=openapi_a, openapi_b=openapi_b)