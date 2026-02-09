import streamlit as st
from crawler import APICrawler
from prompts import create_mapping_prompt
from llm import GeminiClient
import json

st.set_page_config(
    page_title="API Integration Assistant",
    page_icon="🔗",
    layout="wide"
)

st.title("🔗 Universal API Integration Assistant")
st.markdown("Extract API specs from **any** documentation and generate integration blueprints.")

# Sidebar settings
with st.sidebar:
    st.header("⚙️ Crawler Settings")
    max_pages = st.slider("Max pages to crawl", 5, 20, 10)
    crawl_delay = st.slider("Delay between requests (seconds)", 0.5, 3.0, 1.0)
    
    st.info("**Tip:** Start with fewer pages for faster results. Increase if documentation is spread across many pages.")

# Input section
col1, col2 = st.columns(2)

with col1:
    st.subheader("🌐 API A Documentation")
    api_a_url = st.text_input(
        "Enter documentation URL",
        placeholder="https://stripe.com/docs/api/customers",
        help="Can be OpenAPI spec URL or any documentation page",
        key="api_a"
    )
    
    if st.button("🔍 Preview API A"):
        if api_a_url:
            with st.spinner("Fetching preview..."):
                from scraper import WebScraper
                scraper = WebScraper(api_a_url)
                html, error = scraper.fetch_page(api_a_url)
                if error:
                    st.error(error)
                else:
                    cleaned = scraper.clean_html_for_llm(html, max_chars=2000)
                    with st.expander("📄 Cleaned Content Preview"):
                        st.text(cleaned[:1000] + "...")

with col2:
    st.subheader("🌐 API B Documentation")
    api_b_url = st.text_input(
        "Enter documentation URL",
        placeholder="https://docs.github.com/en/rest/users",
        help="Can be OpenAPI spec URL or any documentation page",
        key="api_b"
    )
    
    if st.button("🔍 Preview API B"):
        if api_b_url:
            with st.spinner("Fetching preview..."):
                from scraper import WebScraper
                scraper = WebScraper(api_b_url)
                html, error = scraper.fetch_page(api_b_url)
                if error:
                    st.error(error)
                else:
                    cleaned = scraper.clean_html_for_llm(html, max_chars=2000)
                    with st.expander("📄 Cleaned Content Preview"):
                        st.text(cleaned[:1000] + "...")

# Main analyze button
st.divider()

if st.button("🚀 Analyze & Map APIs", type="primary", use_container_width=True):
    if not api_a_url or not api_b_url:
        st.error("Please provide both API documentation URLs")
    else:
        # Progress containers
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Crawl API A
        status_text.text("🕷️ Crawling API A documentation...")
        
        crawler_a = APICrawler(max_pages=max_pages, delay=crawl_delay)
        
        def update_progress_a(current, total, message):
            progress = int((current / total) * 40)  # 0-40%
            progress_bar.progress(progress)
            status_text.text(f"🕷️ API A: {message}")
        
        data_a = crawler_a.crawl(api_a_url, progress_callback=update_progress_a)
        
        # Crawl API B
        status_text.text("🕷️ Crawling API B documentation...")
        
        crawler_b = APICrawler(max_pages=max_pages, delay=crawl_delay)
        
        def update_progress_b(current, total, message):
            progress = 40 + int((current / total) * 40)  # 40-80%
            progress_bar.progress(progress)
            status_text.text(f"🕷️ API B: {message}")
        
        data_b = crawler_b.crawl(api_b_url, progress_callback=update_progress_b)
        
        # Store in session state
        st.session_state['data_a'] = data_a
        st.session_state['data_b'] = data_b
        
        progress_bar.progress(100)
        status_text.text("✅ Crawling complete!")
        
        st.success(f"""
        ✅ **Extraction Complete!**
        - API A: {len(data_a['endpoints'])} endpoints from {len(data_a['pages_analyzed'])} pages
        - API B: {len(data_b['endpoints'])} endpoints from {len(data_b['pages_analyzed'])} pages
        """)
        
        st.balloons()

# Display results
if 'data_a' in st.session_state and 'data_b' in st.session_state:
    st.divider()
    st.header("📊 Extracted API Information")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🔵 API A")
        data_a = st.session_state['data_a']
        
        st.metric("Endpoints", len(data_a['endpoints']))
        st.metric("Schemas", len(data_a['schemas']))
        st.metric("Pages Analyzed", len(data_a['pages_analyzed']))
        
        with st.expander("📄 View Endpoints"):
            for ep in data_a['endpoints'][:10]:
                st.code(f"{ep.get('method', 'GET')} {ep.get('path', 'N/A')}", language=None)
                if ep.get('description'):
                    st.caption(ep['description'][:100])
        
        with st.expander("🗂️ View Schemas"):
            for schema_name in list(data_a['schemas'].keys())[:5]:
                st.write(f"**{schema_name}**")
                schema = data_a['schemas'][schema_name]
                if 'fields' in schema:
                    for field, details in list(schema['fields'].items())[:5]:
                        st.text(f"  • {field}: {details.get('type', 'unknown')}")
        
        with st.expander("🔗 Pages Crawled"):
            for page in data_a['pages_analyzed']:
                st.text(f"• {page['url'][:60]}... ({page['method']})")
    
    with col2:
        st.subheader("🟢 API B")
        data_b = st.session_state['data_b']
        
        st.metric("Endpoints", len(data_b['endpoints']))
        st.metric("Schemas", len(data_b['schemas']))
        st.metric("Pages Analyzed", len(data_b['pages_analyzed']))
        
        with st.expander("📄 View Endpoints"):
            for ep in data_b['endpoints'][:10]:
                st.code(f"{ep.get('method', 'GET')} {ep.get('path', 'N/A')}", language=None)
                if ep.get('description'):
                    st.caption(ep['description'][:100])
        
        with st.expander("🗂️ View Schemas"):
            for schema_name in list(data_b['schemas'].keys())[:5]:
                st.write(f"**{schema_name}**")
                schema = data_b['schemas'][schema_name]
                if 'fields' in schema:
                    for field, details in list(schema['fields'].items())[:5]:
                        st.text(f"  • {field}: {details.get('type', 'unknown')}")
        
        with st.expander("🔗 Pages Crawled"):
            for page in data_b['pages_analyzed']:
                st.text(f"• {page['url'][:60]}... ({page['method']})")
    
    # Export crawled data
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "💾 Download API A Data (JSON)",
            data=json.dumps(data_a, indent=2),
            file_name="api_a_extracted.json",
            mime="application/json"
        )
    with col2:
        st.download_button(
            "💾 Download API B Data (JSON)",
            data=json.dumps(data_b, indent=2),
            file_name="api_b_extracted.json",
            mime="application/json"
        )