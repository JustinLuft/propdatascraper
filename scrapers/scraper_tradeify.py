import requests
from bs4 import BeautifulSoup
import time
import json
import random
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains

class TradeifyScraper:
    def __init__(self):
        self.base_url = "https://tradeify.co/"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        }
        self.driver = None
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
    def setup_driver(self):
        """Setup Chrome driver with stealth options"""
        chrome_options = Options()
        
        # Basic stealth options
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--disable-plugins-discovery')
        chrome_options.add_argument('--disable-web-security')
        chrome_options.add_argument('--allow-running-insecure-content')
        chrome_options.add_argument('--no-first-run')
        chrome_options.add_argument('--disable-default-apps')
        chrome_options.add_argument('--disable-background-timer-throttling')
        chrome_options.add_argument('--disable-backgrounding-occluded-windows')
        chrome_options.add_argument('--disable-renderer-backgrounding')
        chrome_options.add_argument('--disable-features=TranslateUI')
        chrome_options.add_argument('--disable-ipc-flooding-protection')
        
        # Window size and user agent
        chrome_options.add_argument('--window-size=1366,768')
        chrome_options.add_argument(f'--user-agent={self.headers["User-Agent"]}')
        
        # Optional: uncomment for headless mode
        # chrome_options.add_argument('--headless')
        
        try:
            self.driver = webdriver.Chrome(options=chrome_options)
            
            # Execute script to remove webdriver property
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            # Set additional properties to mimic real browser
            self.driver.execute_script("""
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en']
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5]
                });
            """)
            
            return self.driver
        except Exception as e:
            print(f"Error setting up driver: {e}")
            return None
    
    def random_delay(self, min_delay=1, max_delay=3):
        """Add random delay to mimic human behavior"""
        time.sleep(random.uniform(min_delay, max_delay))
    
    def scrape_with_session(self, url=None):
        """Try scraping with requests session first"""
        if not url:
            url = self.base_url
            
        try:
            print("Attempting to scrape with requests session...")
            
            # Add random delay
            self.random_delay(1, 2)
            
            response = self.session.get(url, timeout=30)
            print(f"Response status code: {response.status_code}")
            
            if response.status_code == 403:
                print("403 Forbidden - trying with different headers")
                return self.scrape_with_alternative_headers(url)
            
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            return self.parse_html_content(soup, response.text)
            
        except requests.exceptions.RequestException as e:
            print(f"Request error: {e}")
            return []
    
    def scrape_with_alternative_headers(self, url):
        """Try with different user agents and headers"""
        user_agents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15'
        ]
        
        for ua in user_agents:
            try:
                print(f"Trying with User-Agent: {ua[:50]}...")
                headers = self.headers.copy()
                headers['User-Agent'] = ua
                
                # Add some randomization
                self.random_delay(2, 4)
                
                response = requests.get(url, headers=headers, timeout=30)
                print(f"Response status: {response.status_code}")
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    return self.parse_html_content(soup, response.text)
                    
            except Exception as e:
                print(f"Error with UA {ua[:20]}: {e}")
                continue
        
        return []
    
    def scrape_pricing_page(self, url=None):
        """Scrape using Selenium with enhanced stealth"""
        if not url:
            url = self.base_url
            
        try:
            if not self.driver:
                self.driver = self.setup_driver()
                if not self.driver:
                    return []
            
            print("Loading page with Selenium...")
            self.driver.get(url)
            
            # Simulate human behavior
            self.random_delay(2, 4)
            
            # Scroll to mimic human behavior
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            self.random_delay(1, 2)
            self.driver.execute_script("window.scrollTo(0, 0);")
            
            # Wait for content to load
            try:
                wait = WebDriverWait(self.driver, 15)
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
            except TimeoutException:
                print("Timeout waiting for page to load")
            
            # Get page source and parse
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            return self.parse_html_content(soup, page_source)
            
        except Exception as e:
            print(f"Error with Selenium scraping: {e}")
            return []
    
    def parse_html_content(self, soup, raw_html):
        """Parse HTML content to extract pricing information"""
        plans = []
        
        try:
            print("Parsing HTML content...")
            
            # Debug: Save HTML to file for inspection
            with open('debug_page.html', 'w', encoding='utf-8') as f:
                f.write(str(soup))
            print("Page content saved to debug_page.html for inspection")
            
            # Look for common pricing selectors
            pricing_selectors = [
                '[class*="pricing"]',
                '[class*="plan"]',
                '[class*="account"]',
                '[class*="card"]',
                '[class*="tier"]',
                '[id*="pricing"]',
                '[id*="plan"]'
            ]
            
            found_elements = []
            for selector in pricing_selectors:
                elements = soup.select(selector)
                found_elements.extend(elements)
                print(f"Found {len(elements)} elements with selector: {selector}")
            
            # Remove duplicates
            found_elements = list(set(found_elements))
            
            # Also search for text containing pricing keywords
            pricing_keywords = ['$', 'price', 'account', 'plan', 'tier', 'pro', 'basic', 'premium']
            text_elements = soup.find_all(text=lambda text: text and any(keyword in text.lower() for keyword in pricing_keywords))
            
            print(f"Found {len(text_elements)} text elements with pricing keywords")
            
            # Extract structured data
            for element in found_elements:
                plan_data = self.extract_plan_data_enhanced(element)
                if plan_data and plan_data.get('plan_name'):
                    plans.append(plan_data)
            
            # If no structured plans found, try to extract from general text
            if not plans:
                print("No structured plans found, attempting text extraction...")
                plans = self.extract_from_text(raw_html)
            
            print(f"Extracted {len(plans)} plans")
            return plans
            
        except Exception as e:
            print(f"Error parsing HTML: {e}")
            return []
    
    def extract_plan_data_enhanced(self, element):
        """Enhanced plan data extraction"""
        try:
            plan_data = {}
            element_text = element.get_text(strip=True)
            
            if not element_text or len(element_text) < 5:
                return None
            
            # Extract plan name from headers
            headers = element.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
            for header in headers:
                header_text = header.get_text(strip=True)
                if header_text and len(header_text) < 50:  # Reasonable plan name length
                    plan_data['plan_name'] = header_text
                    break
            
            # Extract price information
            price_patterns = [
                r'\$[\d,]+(?:\.\d{2})?',
                r'[\d,]+\s*(?:USD|dollars?)',
                r'Price:?\s*\$?[\d,]+',
            ]
            
            import re
            for pattern in price_patterns:
                price_match = re.search(pattern, element_text, re.IGNORECASE)
                if price_match:
                    plan_data['price_raw'] = price_match.group()
                    # Clean price
                    clean_price = re.sub(r'[^\d.]', '', price_match.group())
                    plan_data['price'] = f"${clean_price}" if clean_price else ""
                    break
            
            # Store full text for manual review
            plan_data['full_text'] = element_text[:500]  # First 500 chars
            plan_data['element_tag'] = element.name
            plan_data['element_classes'] = element.get('class', [])
            
            return plan_data
            
        except Exception as e:
            print(f"Error extracting enhanced plan data: {e}")
            return None
    
    def extract_from_text(self, html_content):
        """Extract pricing info from raw text when structured extraction fails"""
        plans = []
        
        try:
            import re
            
            # Look for common pricing patterns in the HTML
            price_patterns = [
                r'(\w+\s+(?:Account|Plan|Tier))[:\s]*\$?([\d,]+(?:\.\d{2})?)',
                r'\$?([\d,]+(?:\.\d{2})?)[:\s]*(?:for|per)?[:\s]*(\w+\s+(?:Account|Plan|Tier))',
            ]
            
            for pattern in price_patterns:
                matches = re.finditer(pattern, html_content, re.IGNORECASE)
                for match in matches:
                    plan_data = {
                        'plan_name': match.group(1) if len(match.groups()) > 1 else 'Unknown Plan',
                        'price_raw': match.group(0),
                        'extraction_method': 'regex'
                    }
                    plans.append(plan_data)
            
            return plans[:5]  # Limit to first 5 matches to avoid noise
            
        except Exception as e:
            print(f"Error in text extraction: {e}")
            return []
    
    def scrape(self, url=None):
        """Main scraping method with fallback strategies"""
        print("Starting Tradeify scraper...")
        
        try:
            # Strategy 1: Try requests session first (fastest)
            plans = self.scrape_with_session(url)
            
            if plans:
                print(f"Successfully scraped {len(plans)} plans with requests")
                return plans
            
            # Strategy 2: Try Selenium
            print("Requests failed, trying Selenium...")
            plans = self.scrape_pricing_page(url)
            
            if plans:
                print(f"Successfully scraped {len(plans)} plans with Selenium")
                return plans
            
            print("All scraping methods failed")
            return []
            
        except Exception as e:
            print(f"Error in main scrape method: {e}")
            return []
        finally:
            if self.driver:
                self.driver.quit()
    
    def save_to_json(self, data, filename="tradeify_data.json"):
        """Save scraped data to JSON file"""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"Data saved to {filename}")
        except Exception as e:
            print(f"Error saving to JSON: {e}")

def scrape_site_tradeify():
    """Function to be called from main.py"""
    scraper = TradeifyScraper()
    data = scraper.scrape()
    
    # Process data for CSV output
    processed_data = []
    for plan in data:
        row = {
            'site': 'Tradeify',
            'plan_name': plan.get('plan_name', ''),
            'price': plan.get('price', ''),
            'price_raw': plan.get('price_raw', ''),
            'full_text': plan.get('full_text', ''),
            'extraction_method': plan.get('extraction_method', 'structured'),
            'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Add features as separate columns
        features = plan.get('features', {})
        for feature_key, feature_value in features.items():
            row[feature_key] = feature_value
        
        processed_data.append(row)
    
    # Save debug data
    scraper.save_to_json(processed_data)
    
    return processed_data

# Test function
if __name__ == "__main__":
    data = scrape_site_tradeify()
    print(f"Scraped {len(data)} plans")
    for plan in data:
        print(f"Plan: {plan.get('plan_name', 'Unknown')}")
        print(f"Price: {plan.get('price', 'N/A')}")
        print("---")
