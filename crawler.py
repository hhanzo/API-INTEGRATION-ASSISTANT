from typing import Dict, List, Set
from scraper import WebScraper
from extractor import APIExtractor
import json
import time

class APICrawler:
    def __init__(self, max_pages: int = 15, delay: float = 1.0):
        """
        Args:
            max_pages: Maximum pages to crawl
            delay: Delay between requests (seconds) - be respectful!
        """
        self.max_pages = max_pages
        self.delay = delay
        self.visited_urls: Set[str] = set()
        self.extractor = APIExtractor()
        self.crawl_data = {
            'endpoints': [],
            'schemas': {},
            'auth': None,
            'api_info': {},
            'pages_analyzed': []
        }
    
    def crawl(self, start_url: str, progress_callback=None) -> Dict:
        """
        Crawl API documentation starting from start_url.
        
        Args:
            start_url: Starting URL
            progress_callback: Function to call with progress updates
            
        Returns:
            Aggregated API information
        """
        to_visit = [start_url]
        self.visited_urls = set()
        
        iteration = 0
        
        while to_visit and iteration < self.max_pages:
            url = to_visit.pop(0)
            
            # Skip if already visited
            if url in self.visited_urls:
                continue
            
            if progress_callback:
                progress_callback(
                    iteration + 1,
                    self.max_pages,
                    f"Analyzing: {url[:50]}..."
                )
            
            print(f"\n[{iteration + 1}/{self.max_pages}] Crawling: {url}")
            
            # Extract from this page
            result = self.extractor.extract_from_url(url)
            
            if result['success']:
                # Merge data
                self._merge_data(result['data'], url, result['method'])
                
                # Get suggested URLs for next iteration
                if result['method'] == 'llm_extraction':
                    data = result['data']
                    if data.get('needs_more_pages') and data.get('suggested_urls'):
                        # Add suggested URLs to crawl
                        for suggested_url in data['suggested_urls'][:3]:
                            if suggested_url not in self.visited_urls:
                                to_visit.append(suggested_url)
                
                # Also get links from the page itself
                if result['method'] == 'llm_extraction' and iteration < 5:
                    # Only do link discovery for first few pages
                    scraper = WebScraper(url)
                    html, _ = scraper.fetch_page(url)
                    if html:
                        links = scraper.find_api_documentation_links(html, url)
                        # Add top 3 links
                        for link in links[:3]:
                            if link not in self.visited_urls and link not in to_visit:
                                to_visit.append(link)
            
            self.visited_urls.add(url)
            iteration += 1
            
            # Be respectful - delay between requests
            time.sleep(self.delay)
        
        if progress_callback:
            progress_callback(
                self.max_pages,
                self.max_pages,
                f"Complete! Analyzed {len(self.visited_urls)} pages"
            )
        
        return self.crawl_data
    
    def _merge_data(self, new_data: Dict, url: str, method: str):
        """Merge newly extracted data into aggregated crawl_data."""
        
        # Track which page this came from
        self.crawl_data['pages_analyzed'].append({
            'url': url,
            'method': method
        })
        
        if method == 'openapi':
            # OpenAPI format
            self.crawl_data['api_info'] = new_data.get('info', {})
            self.crawl_data['endpoints'].extend(new_data.get('endpoints', []))
            self.crawl_data['schemas'].update(new_data.get('schemas', {}))
            if new_data.get('auth'):
                self.crawl_data['auth'] = new_data['auth']
        
        else:
            # LLM extracted format
            if new_data.get('api_info'):
                self.crawl_data['api_info'].update(new_data['api_info'])
            
            # Add endpoints (avoiding duplicates)
            for endpoint in new_data.get('endpoints', []):
                # Check if endpoint already exists
                endpoint_key = f"{endpoint.get('method')}:{endpoint.get('path')}"
                existing_keys = [
                    f"{ep.get('method')}:{ep.get('path')}" 
                    for ep in self.crawl_data['endpoints']
                ]
                
                if endpoint_key not in existing_keys:
                    self.crawl_data['endpoints'].append(endpoint)
                else:
                    # Update existing endpoint with more details
                    idx = existing_keys.index(endpoint_key)
                    self.crawl_data['endpoints'][idx] = self._merge_endpoints(
                        self.crawl_data['endpoints'][idx],
                        endpoint
                    )
            
            # Merge schemas
            for schema_name, schema_data in new_data.get('schemas', {}).items():
                if schema_name in self.crawl_data['schemas']:
                    # Merge fields
                    self.crawl_data['schemas'][schema_name]['fields'].update(
                        schema_data.get('fields', {})
                    )
                else:
                    self.crawl_data['schemas'][schema_name] = schema_data
            
            # Update auth if not set
            if not self.crawl_data['auth'] and new_data.get('authentication'):
                self.crawl_data['auth'] = new_data['authentication']
    
    def _merge_endpoints(self, existing: Dict, new: Dict) -> Dict:
        """Merge two endpoint definitions, preferring more complete data."""
        merged = existing.copy()
        
        # Update fields if new has more info
        for key, value in new.items():
            if key == 'parameters':
                # Merge parameter lists
                existing_params = {p['name']: p for p in existing.get('parameters', [])}
                for param in value:
                    if param['name'] in existing_params:
                        existing_params[param['name']].update(param)
                    else:
                        existing_params[param['name']] = param
                merged['parameters'] = list(existing_params.values())
            
            elif not existing.get(key) and value:
                # If existing doesn't have this field, add it
                merged[key] = value
            elif value and len(str(value)) > len(str(existing.get(key, ''))):
                # If new value is more detailed, use it
                merged[key] = value
        
        return merged