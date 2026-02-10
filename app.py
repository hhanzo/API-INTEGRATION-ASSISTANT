import streamlit as st
from extractor import APIExtractor
from openapi_builder import build_openapi_spec, validate_openapi_spec
import json
import yaml

st.set_page_config(
    page_title="API Integration Assistant",
    page_icon="🔗",
    layout="wide"
)

st.title("🔗 Universal API Integration Assistant")
st.markdown("Extract API specs from **any** documentation and generate **OpenAPI 3.1.0** specifications.")

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