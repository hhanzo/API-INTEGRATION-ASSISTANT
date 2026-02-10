import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlunparse
from typing import Dict, List, Set, Optional, Tuple
import re
import time
from readability.readability import Document
from urllib.parse import urlparse, urlunparse

class WebScraper:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.domain = urlparse(base_url).netloc
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; API-Integration-Assistant/1.0)',
            'Accept': 'text/html,application/json,application/yaml'
        })
    
    def fetch_page(self, url: str, use_readability: bool = False) -> Tuple[Optional[str], Optional[str]]:
        """
        Fetch and clean a web page.
        
        Args:
            url: URL to fetch
            use_readability: Use readability to extract main content
            
        Returns:
            Tuple of (cleaned_html, error_message)
        """
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            if use_readability:
                # Extract main content using readability
                doc = Document(response.text)
                return doc.summary(), None
            else:
                return response.text, None
                
        except requests.Timeout:
            return None, f"Timeout fetching {url}"
        except requests.HTTPError as e:
            return None, f"HTTP {e.response.status_code}: {url}"
        except Exception as e:
            return None, f"Error: {str(e)}"
    
    def clean_html_for_llm(self, html: str, max_chars: int = 30000) -> str:
        """
        Clean HTML and extract text relevant for API documentation.
        Keeps code blocks, tables, and structured content.
        """
        soup = BeautifulSoup(html, 'lxml')
        
        # Remove unwanted elements
        for tag in soup(['script', 'style', 'nav', 'footer', 'header', 
                        'aside', 'iframe', 'noscript', 'svg']):
            tag.decompose()
        
        # Remove navigation and sidebar classes
        for class_name in ['navigation', 'sidebar', 'menu', 'footer', 
                           'header', 'cookie', 'banner', 'ad']:
            for element in soup.find_all(class_=re.compile(class_name, re.I)):
                element.decompose()
        
        # Preserve important structures
        preserved_tags = ['code', 'pre', 'table', 'h1', 'h2', 'h3', 
                         'h4', 'p', 'li', 'dd', 'dt']
        
        # Get text with structure
        cleaned_parts = []
        
        for tag in soup.find_all(preserved_tags):
            if tag.name in ['h1', 'h2', 'h3', 'h4']:
                cleaned_parts.append(f"\n## {tag.get_text(strip=True)}\n")
            elif tag.name in ['code', 'pre']:
                cleaned_parts.append(f"\n```\n{tag.get_text()}\n```\n")
            elif tag.name == 'table':
                cleaned_parts.append(self._table_to_text(tag))
            else:
                text = tag.get_text(strip=True)
                if text:
                    cleaned_parts.append(text)
        
        cleaned = '\n'.join(cleaned_parts)
        
        # Truncate if too long
        if len(cleaned) > max_chars:
            cleaned = cleaned[:max_chars] + "\n\n[... content truncated ...]"
        
        return cleaned
    
    def _table_to_text(self, table) -> str:
        """Convert HTML table to readable text."""
        rows = []
        for tr in table.find_all('tr'):
            cells = [td.get_text(strip=True) for td in tr.find_all(['td', 'th'])]
            rows.append(' | '.join(cells))
        return '\n' + '\n'.join(rows) + '\n'
    
    def find_api_documentation_links(self, html: str, current_url: str) -> List[str]:
        """
        Find links that likely contain API documentation.
        Uses heuristics to identify relevant pages.
        """
        soup = BeautifulSoup(html, 'lxml')
        links = set()
        
        # API documentation indicators
        api_patterns = [
            r'/api/', r'/docs?/', r'/reference/', r'/guide/',
            r'/v\d+/', r'/endpoints?/', r'/resources?/',
            r'/schema/', r'/objects?/', r'/methods?/'
        ]
        
        # Patterns to avoid
        avoid_patterns = [
            r'/blog/', r'/news/', r'/pricing/', r'/about/',
            r'/careers/', r'/contact/', r'/privacy/', r'/terms/',
            r'/changelog/', r'/status/', r'/support/', r'/help/'
        ]
        
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            full_url = urljoin(current_url, href)
            
            # Must be same domain
            if urlparse(full_url).netloc != self.domain:
                continue
            
            # Check if URL matches API patterns
            url_lower = full_url.lower()
            
            if any(re.search(pattern, url_lower) for pattern in api_patterns):
                # Make sure it doesn't match avoid patterns
                if not any(re.search(pattern, url_lower) for pattern in avoid_patterns):
                    links.add(full_url)
            
            # Also check link text for API-related keywords
            link_text = a_tag.get_text(strip=True).lower()
            api_keywords = ['api', 'endpoint', 'reference', 'schema', 
                           'object', 'method', 'request', 'response']
            
            if any(keyword in link_text for keyword in api_keywords):
                if not any(re.search(pattern, url_lower) for pattern in avoid_patterns):
                    links.add(full_url)
        
        return list(links)

    def split_by_h2_sections(self, html: str, max_chars=12000):
        soup = BeautifulSoup(html, "lxml")

        sections = []
        current = []
        current_len = 0

        for el in soup.find_all(["h2", "h3", "p", "pre", "code", "table", "ul", "ol"]):
            if el.name == "h2" and current:
                sections.append(current)
                current = []
                current_len = 0

            text = el.get_text("\n", strip=True)
            if not text:
                continue

            current.append(text)
            current_len += len(text)

            if current_len >= max_chars:
                sections.append(current)
                current = []
                current_len = 0

        if current:
            sections.append(current)

        return ["\n".join(s) for s in sections]

    def _llm_extract_from_html(self, html: str, url: str):

    # 1. split into logical documentation sections
        sections = self.scraper.split_by_h2_sections(html)

        aggregated = {
            "api_info": {},
            "endpoints": [],
            "common_schemas": {},
            "authentication": None,
            "needs_more_pages": False,
            "suggested_urls": []
        }

        for section in sections:

            # 2. light clean per section (not full page flattening)
            cleaned_section = self.scraper.clean_text_block_for_llm(section)

            if not cleaned_section or len(cleaned_section) < 200:
                continue

            prompt = self._create_extraction_prompt(
                cleaned_section,
                url
            )

            result = self.llm.analyze_apis(prompt)

            if not result or not result.get("parsed"):
                continue

            data = result["parsed"]

            # ---- merge api info
            if data.get("api_info"):
                aggregated["api_info"].update(
                    {k: v for k, v in data["api_info"].items() if v}
                )

            # ---- merge endpoints
            for ep in data.get("endpoints", []):
                aggregated["endpoints"].append(ep)

            # ---- merge common schemas
            aggregated["common_schemas"].update(
                data.get("common_schemas", {}) or {}
            )

            # ---- first auth wins
            if not aggregated["authentication"] and data.get("authentication"):
                aggregated["authentication"] = data["authentication"]

            # ---- propagate flags
            if data.get("needs_more_pages"):
                aggregated["needs_more_pages"] = True

            # ---- suggested urls
            aggregated["suggested_urls"].extend(
                data.get("suggested_urls", []) or []
            )

        # 3. de-duplicate suggested urls
        aggregated["suggested_urls"] = list(
            dict.fromkeys(aggregated["suggested_urls"])
        )

        return aggregated

    import re

    def clean_text_block_for_llm(self, text: str) -> str:
        """
         Light cleaning for already extracted section text.
         Keeps structure and ordering.
        """

        # collapse excessive whitespace
        text = re.sub(r"\n{3,}", "\n\n", text)

        # remove very common UI garbage that still leaks in
        garbage = [
            "Copy",
            "Copied!",
            "Edit this page",
            "On this page"
        ]

        lines = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                lines.append("")
                continue

            if line in garbage:
                continue

            lines.append(line)

        return "\n".join(lines).strip()
