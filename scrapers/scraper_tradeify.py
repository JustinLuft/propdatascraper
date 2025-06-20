
import requests
from bs4 import BeautifulSoup
import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

class TradeifyScraper:
    def __init__(self):
        self.base_url = "https://tradeify.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        self.driver = None
        
    def setup_driver(self):
        """Setup Chrome driver with options"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument(f'--user-agent={self.headers["User-Agent"]}')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        return self.driver
    
    def scrape_pricing_page(self, url=None):
        """Scrape the pricing page for account plans"""
        if not url:
            url = f"{self.base_url}/pricing"  # Adjust URL as needed
            
        try:
            if not self.driver:
                self.setup_driver()
                
            self.driver.get(url)
            
            # Wait for pricing cards to load
            wait = WebDriverWait(self.driver, 10)
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, "pricing-card")))
            
            plans = []
            
            # Look for pricing cards - adjust selectors based on actual HTML structure
            pricing_cards = self.driver.find_elements(By.CSS_SELECTOR, "[class*='account'], [class*='plan'], [class*='pricing']")
            
            for card in pricing_cards:
                try:
                    plan_data = self.extract_plan_data(card)
                    if plan_data:
                        plans.append(plan_data)
                except Exception as e:
                    print(f"Error extracting plan data: {e}")
                    continue
                    
            return plans
            
        except TimeoutException:
            print("Timeout waiting for pricing page to load")
            return []
        except Exception as e:
            print(f"Error scraping pricing page: {e}")
            return []
    
    def extract_plan_data(self, card_element):
        """Extract data from a pricing card element"""
        try:
            plan_data = {}
            
            # Extract plan name/account size
            plan_name_selectors = [
                "h3", "h2", "[class*='title']", "[class*='account']", 
                "[class*='plan-name']", ".account-title"
            ]
            
            plan_name = self.find_text_by_selectors(card_element, plan_name_selectors)
            if plan_name:
                plan_data['plan_name'] = plan_name.strip()
            
            # Extract price
            price_selectors = [
                "[class*='price']", "[class*='cost']", "[class*='fee']",
                "span:contains('$')", "div:contains('$')"
            ]
            
            price = self.find_text_by_selectors(card_element, price_selectors)
            if price:
                # Clean up price text
                price_clean = ''.join(filter(lambda x: x.isdigit() or x == '$', price))
                plan_data['price'] = price_clean
                plan_data['price_raw'] = price.strip()
            
            # Extract features/specifications
            features = {}
            
            # Common feature patterns to look for
            feature_patterns = {
                'max_contracts': ['Max Contracts', 'Contracts', 'Minis', 'Micros'],
                'daily_loss_limit': ['Daily Loss Limit', 'Loss Limit', 'Soft Breach'],
                'trailing_drawdown': ['Trailing Max Drawdown', 'Max Drawdown', 'Drawdown'],
                'drawdown_mode': ['Drawdown Mode'],
                'min_trading_days': ['Min Trading Days', 'Trading Days', 'Payout'],
                'consistency': ['Consistency'],
                'max_accounts': ['Max Accounts']
            }
            
            # Get all text content from the card
            card_text = card_element.text
            
            for feature_key, keywords in feature_patterns.items():
                for keyword in keywords:
                    if keyword.lower() in card_text.lower():
                        # Try to extract the value after the keyword
                        lines = card_text.split('\n')
                        for line in lines:
                            if keyword.lower() in line.lower():
                                # Extract value from the line
                                value = self.extract_feature_value(line, keyword)
                                if value:
                                    features[feature_key] = value
                                break
            
            plan_data['features'] = features
            plan_data['full_text'] = card_text
            
            return plan_data
            
        except Exception as e:
            print(f"Error extracting plan data: {e}")
            return None
    
    def find_text_by_selectors(self, parent_element, selectors):
        """Try multiple selectors to find text content"""
        for selector in selectors:
            try:
                elements = parent_element.find_elements(By.CSS_SELECTOR, selector)
                for element in elements:
                    text = element.text.strip()
                    if text:
                        return text
            except:
                continue
        return None
    
    def extract_feature_value(self, line, keyword):
        """Extract value from a feature line"""
        try:
            # Remove the keyword and clean up
            value = line.replace(keyword, '').strip()
            value = value.lstrip(':').strip()
            return value
        except:
            return None
    
    def scrape_with_requests(self, url=None):
        """Alternative scraping method using requests (for static content)"""
        if not url:
            url = f"{self.base_url}/pricing"
            
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for pricing information in the HTML
            plans = []
            
            # Adjust these selectors based on the actual HTML structure
            pricing_sections = soup.find_all(['div', 'section'], class_=lambda x: x and any(
                keyword in x.lower() for keyword in ['pricing', 'plan', 'account', 'card']
            ))
            
            for section in pricing_sections:
                plan_data = self.extract_plan_data_bs4(section)
                if plan_data:
                    plans.append(plan_data)
            
            return plans
            
        except requests.RequestException as e:
            print(f"Error making request: {e}")
            return []
    
    def extract_plan_data_bs4(self, section):
        """Extract plan data using BeautifulSoup"""
        try:
            plan_data = {}
            text = section.get_text()
            
            # Extract plan name
            title_elem = section.find(['h1', 'h2', 'h3', 'h4'])
            if title_elem:
                plan_data['plan_name'] = title_elem.get_text().strip()
            
            # Extract price
            price_elem = section.find(text=lambda text: text and '$' in text)
            if price_elem:
                plan_data['price_raw'] = price_elem.strip()
            
            plan_data['full_text'] = text
            return plan_data
            
        except Exception as e:
            print(f"Error extracting BS4 plan data: {e}")
            return None
    
    def scrape(self, url=None):
        """Main scraping method"""
        try:
            # Try Selenium first (better for dynamic content)
            plans = self.scrape_pricing_page(url)
            
            # If Selenium fails or returns empty, try requests
            if not plans:
                print("Selenium scraping failed, trying requests...")
                plans = self.scrape_with_requests(url)
            
            return plans
            
        except Exception as e:
            print(f"Error in main scrape method: {e}")
            return []
        finally:
            if self.driver:
                self.driver.quit()
    
    def save_to_json(self, data, filename="tradeify_data.json"):
        """Save scraped data to JSON file"""
        try:
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
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
            'scraped_at': time.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        # Add features as separate columns
        features = plan.get('features', {})
        for feature_key, feature_value in features.items():
            row[feature_key] = feature_value
        
        processed_data.append(row)
    
    return processed_data
