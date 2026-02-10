import streamlit as st
from crawler import APICrawler
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
        
        # Crawl API A
        status_text.text("🕷️ Extracting API A...")
        
        crawler_a = APICrawler(max_pages=max_pages, delay=crawl_delay)
        
        def update_progress_a(current, total, message):
            progress = int((current / total) * 45)
            progress_bar.progress(progress)
            status_text.text(f"🕷️ API A: {message}")
        
        data_a = crawler_a.crawl(api_a_url, progress_callback=update_progress_a)
        
        # Build OpenAPI spec for A
        status_text.text("🔨 Building OpenAPI spec for API A...")
        progress_bar.progress(48)
        openapi_a = build_openapi_spec(data_a)
        openapi_a['info']['x-source-url'] = api_a_url
        
        # Validate
        is_valid_a, errors_a = validate_openapi_spec(openapi_a)
        
        # Crawl API B
        status_text.text("🕷️ Extracting API B...")
        
        crawler_b = APICrawler(max_pages=max_pages, delay=crawl_delay)
        
        def update_progress_b(current, total, message):
            progress = 50 + int((current / total) * 45)
            progress_bar.progress(progress)
            status_text.text(f"🕷️ API B: {message}")
        
        data_b = crawler_b.crawl(api_b_url, progress_callback=update_progress_b)
        
        # Build OpenAPI spec for B
        status_text.text("🔨 Building OpenAPI spec for API B...")
        progress_bar.progress(98)
        openapi_b = build_openapi_spec(data_b)
        openapi_b['info']['x-source-url'] = api_b_url
        
        # Validate
        is_valid_b, errors_b = validate_openapi_spec(openapi_b)
        
        progress_bar.progress(100)
        status_text.text("✅ Extraction complete!")
        
        # Store in session state
        st.session_state['openapi_a'] = openapi_a
        st.session_state['openapi_b'] = openapi_b
        st.session_state['is_valid_a'] = is_valid_a
        st.session_state['is_valid_b'] = is_valid_b
        st.session_state['errors_a'] = errors_a
        st.session_state['errors_b'] = errors_b
        
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