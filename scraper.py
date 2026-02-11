import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import List, Optional, Tuple
import re
from readability.readability import Document

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
