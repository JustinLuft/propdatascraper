import requests
from bs4 import BeautifulSoup
import json
import re
import time
import random
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import csv
from urllib.parse import urljoin
from abc import ABC, abstractmethod

@dataclass
class TradingPlan:
    business_name: str
    account_size: str
    sale_price: str
    funded_full_price: str
    discount_code: str
    trial_type: str
    trustpilot_score: str
    profit_goal: str
    additional_info: Dict

class BaseScraper(ABC):
    """Base scraper class with common functionality"""
    
    def __init__(self, base_url: str, business_name: str):
        self.base_url = base_url.rstrip('/')
        self.business_name = business_name
        self.session = requests.Session()
        self.plans = []
        
        # Common headers - can be overridden by subclasses
        self.session.headers.update(self._get_default_headers())
        
    def _get_default_headers(self) -> Dict[str, str]:
        """Default headers for requests"""
        return {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
        }
    
    def _get_user_agents(self) -> List[str]:
        """Get list of user agents for rotation"""
        return [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0'
        ]
    
    def _make_request(self, url: str, max_retries: int = 3) -> Optional[requests.Response]:
        """Make a request with retry logic and random delays"""
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    delay = random.uniform(2, 5)
                    print(f"Retrying in {delay:.1f} seconds...")
                    time.sleep(delay)
                
                # Rotate User-Agent for each retry
                self.session.headers['User-Agent'] = random.choice(self._get_user_agents())
                
                print(f"Attempting to fetch: {url} (attempt {attempt + 1})")
                
                response = self.session.get(url, timeout=30)
                
                if response.status_code == 200:
                    print(f"Successfully fetched {url}")
                    return response
                elif response.status_code == 403:
                    print(f"403 Forbidden for {url} - attempting with different approach")
                    self._handle_403_error()
                elif response.status_code == 429:
                    print(f"Rate limited - waiting longer before retry")
                    time.sleep(random.uniform(10, 20))
                else:
                    print(f"HTTP {response.status_code} for {url}")
                    
            except requests.RequestException as e:
                print(f"Request error on attempt {attempt + 1}: {e}")
                if attempt == max_retries - 1:
                    print(f"Failed to fetch {url} after {max_retries} attempts")
        
        return None
    
    def _handle_403_error(self):
        """Handle 403 errors by updating headers"""
        self.session.headers.update({
            'Referer': 'https://www.google.com/',
            'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'Sec-Ch-Ua-Mobile': '?0',
            'Sec-Ch-Ua-Platform': '"Windows"'
        })
    
    def _extract_text_by_selectors(self, soup: BeautifulSoup, selectors: List[str], default: str = "") -> str:
        """Extract text using multiple selectors as fallback"""
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                if text:
                    return text
        return default
    
    def _extract_price_from_text(self, text: str) -> str:
        """Extract price from text using common patterns"""
        price_patterns = [
            r'\$(\d+(?:,\d{3})*(?:\.\d{2})?)',
            r'(\d+(?:,\d{3})*)\s*(?:USD|dollars?)',
            r'Price:\s*\$?(\d+(?:,\d{3})*(?:\.\d{2})?)',
        ]
        
        for pattern in price_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return f"${match.group(1)}"
        return ""
    
    def _extract_trustpilot_score(self, soup: BeautifulSoup) -> str:
        """Generic Trustpilot score extraction"""
        trustpilot_selectors = [
            '[class*="trustpilot"]',
            '[data-testid*="trustpilot"]',
            '.tp-widget',
            '[src*="trustpilot"]'
        ]
        
        for selector in trustpilot_selectors:
            element = soup.select_one(selector)
            if element:
                for attr in ['data-score', 'data-rating', 'data-stars']:
                    if element.get(attr):
                        return element[attr]
                
                text = element.get_text()
                score_match = re.search(r'(\d+\.?\d*)\s*(?:out of 5|/5|stars?)', text)
                if score_match:
                    return score_match.group(1)
        
        return self.get_default_trustpilot_score()
    
    def _extract_discount_codes(self, soup: BeautifulSoup) -> str:
        """Generic discount code extraction"""
        discount_patterns = [
            r'(?:code|coupon):\s*([A-Z0-9]+)',
            r'use\s+(?:code|coupon)\s+([A-Z0-9]+)',
            r'promo\s*code:\s*([A-Z0-9]+)',
            r'discount\s*code:\s*([A-Z0-9]+)'
        ]
        
        text = soup.get_text()
        
        for pattern in discount_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return "Contact for codes"
    
    # Abstract methods that must be implemented by subclasses
    @abstractmethod
    def get_main_urls(self) -> List[str]:
        """Return list of main URLs to scrape"""
        pass
    
    @abstractmethod
    def extract_plans_from_soup(self, soup: BeautifulSoup, url: str) -> List[Dict]:
        """Extract trading plans from soup - must be implemented by subclass"""
        pass
    
    @abstractmethod
    def get_fallback_plans(self) -> List[Dict]:
        """Return fallback plans when scraping fails"""
        pass
    
    # Optional methods that can be overridden
    def get_additional_urls(self) -> List[str]:
        """Return additional URLs to scrape (optional)"""
        return []
    
    def get_default_trustpilot_score(self) -> str:
        """Return default Trustpilot score"""
        return "4.0"
    
    def process_plan_data(self, plan_data: Dict) -> Dict:
        """Process raw plan data before creating TradingPlan object"""
        return plan_data
    
    # Main scraping logic
    def scrape_all(self) -> List[TradingPlan]:
        """Main method to scrape all pages"""
        all_urls = self.get_main_urls() + self.get_additional_urls()
        
        for url in all_urls:
            try:
                response = self._make_request(url)
                if response:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    plans = self.extract_plans_from_soup(soup, url)
                    
                    for plan_data in plans:
                        processed_data = self.process_plan_data(plan_data)
                        plan = self._create_trading_plan(processed_data, soup)
                        if plan:
                            self.plans.append(plan)
                
                # Random delay between requests
                time.sleep(random.uniform(1, 3))
                
            except Exception as e:
                print(f"Error scraping {url}: {e}")
                continue
        
        # If no plans were scraped, use fallback
        if not self.plans:
            print("No plans scraped - using fallback data")
            fallback_plans = self.get_fallback_plans()
            for plan_data in fallback_plans:
                plan = self._create_trading_plan_from_dict(plan_data)
                if plan:
                    self.plans.append(plan)
        
        return self.plans
    
    def _create_trading_plan(self, plan_data: Dict, soup: BeautifulSoup) -> Optional[TradingPlan]:
        """Create TradingPlan object from extracted data"""
        try:
            return TradingPlan(
                business_name=self.business_name,
                account_size=plan_data.get('account_size', ''),
                sale_price=plan_data.get('sale_price', ''),
                funded_full_price=plan_data.get('funded_full_price', ''),
                discount_code=plan_data.get('discount_code') or self._extract_discount_codes(soup),
                trial_type=plan_data.get('trial_type', 'Account'),
                trustpilot_score=plan_data.get('trustpilot_score') or self._extract_trustpilot_score(soup),
                profit_goal=plan_data.get('profit_goal', ''),
                additional_info=plan_data
            )
        except Exception as e:
            print(f"Error creating trading plan: {e}")
            return None
    
    def _create_trading_plan_from_dict(self, plan_data: Dict) -> Optional[TradingPlan]:
        """Create TradingPlan object from dictionary (for fallback data)"""
        try:
            return TradingPlan(
                business_name=self.business_name,
                account_size=plan_data.get('account_size', ''),
                sale_price=plan_data.get('sale_price', ''),
                funded_full_price=plan_data.get('funded_full_price', ''),
                discount_code=plan_data.get('discount_code', 'Contact for codes'),
                trial_type=plan_data.get('trial_type', 'Account'),
                trustpilot_score=plan_data.get('trustpilot_score', self.get_default_trustpilot_score()),
                profit_goal=plan_data.get('profit_goal', ''),
                additional_info=plan_data
            )
        except Exception as e:
            print(f"Error creating trading plan from dict: {e}")
            return None
    
    # Utility methods
    def save_to_csv(self, filename: str = None):
        """Save scraped data to CSV file"""
        if not filename:
            filename = f"{self.business_name.lower().replace(' ', '_')}_data.csv"
        
        if not self.plans:
            print("No data to save")
            return
        
        fieldnames = [
            'business_name', 'account_size', 'sale_price', 'funded_full_price',
            'discount_code', 'trial_type', 'trustpilot_score', 'profit_goal'
        ]
        
        # Add additional fields from the first plan
        if self.plans and self.plans[0].additional_info:
            additional_fields = list(self.plans[0].additional_info.keys())
            fieldnames.extend([f for f in additional_fields if f not in fieldnames])
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for plan in self.plans:
                row = {
                    'business_name': plan.business_name,
                    'account_size': plan.account_size,
                    'sale_price': plan.sale_price,
                    'funded_full_price': plan.funded_full_price,
                    'discount_code': plan.discount_code,
                    'trial_type': plan.trial_type,
                    'trustpilot_score': plan.trustpilot_score,
                    'profit_goal': plan.profit_goal,
                }
                
                # Add additional info
                if plan.additional_info:
                    row.update(plan.additional_info)
                
                writer.writerow(row)
        
        print(f"Data saved to {filename}")
    
    def save_to_json(self, filename: str = None):
        """Save scraped data to JSON file"""
        if not filename:
            filename = f"{self.business_name.lower().replace(' ', '_')}_data.json"
        
        if not self.plans:
            print("No data to save")
            return
        
        data = []
        for plan in self.plans:
            data.append({
                'business_name': plan.business_name,
                'account_size': plan.account_size,
                'sale_price': plan.sale_price,
                'funded_full_price': plan.funded_full_price,
                'discount_code': plan.discount_code,
                'trial_type': plan.trial_type,
                'trustpilot_score': plan.trustpilot_score,
                'profit_goal': plan.profit_goal,
                'additional_info': plan.additional_info
            })
        
        with open(filename, 'w', encoding='utf-8') as jsonfile:
            json.dump(data, jsonfile, indent=2, ensure_ascii=False)
        
        print(f"Data saved to {filename}")
    
    def print_results(self):
        """Print scraped results to console"""
        if not self.plans:
            print("No data scraped")
            return
        
        print(f"\n{'='*60}")
        print(f"{self.business_name.upper()} SCRAPING RESULTS")
        print(f"{'='*60}")
        
        for i, plan in enumerate(self.plans, 1):
            print(f"\nPlan {i}:")
            print(f"  Business Name: {plan.business_name}")
            print(f"  Account Size: {plan.account_size}")
            print(f"  Trial Type: {plan.trial_type}")
            print(f"  Sale Price: {plan.sale_price}")
            print(f"  Funded Full Price: {plan.funded_full_price}")
            print(f"  Discount Code: {plan.discount_code}")
            print(f"  Trustpilot Score: {plan.trustpilot_score}")
            print(f"  Profit Goal: {plan.profit_goal}")
            if plan.additional_info:
                print(f"  Additional Info:")
                for key, value in plan.additional_info.items():
                    if key not in ['account_size', 'sale_price', 'profit_goal', 'trial_type']:
                        print(f"    {key}: {value}")
            print("-" * 40)
    
    def get_standardized_data(self) -> List[Dict]:
        """Return data in standardized format"""
        standardized_data = []
        for plan in self.plans:
            standardized_data.append({
                'business_name': plan.business_name,
                'plan_name': f"{plan.account_size} {plan.trial_type}",
                'account_size': plan.account_size,
                'price_raw': plan.sale_price,
                'funded_price': plan.funded_full_price,
                'discount_code': plan.discount_code,
                'trial_type': plan.trial_type,
                'trustpilot_score': plan.trustpilot_score,
                'profit_goal': plan.profit_goal,
                'source': self.business_name
            })
        return standardized_data


# Example implementation for Apex Trader Funding
class ApexTraderFundingScraper(BaseScraper):
    def __init__(self):
        super().__init__("https://apextraderfunding.com", "Apex Trader Funding")
    
    def get_main_urls(self) -> List[str]:
        return [self.base_url]
    
    def get_additional_urls(self) -> List[str]:
        return [
            f"{self.base_url}/pricing",
            f"{self.base_url}/plans",
            f"{self.base_url}/evaluation",
            f"{self.base_url}/funded-accounts"
        ]
    
    def extract_plans_from_soup(self, soup: BeautifulSoup, url: str) -> List[Dict]:
        """Extract Apex-specific pricing plans"""
        plans = []
        
        pricing_selectors = [
            '.pricing__item.pricing__item--style2',
            '.pricing__item',
            '[class*="pricing__item"]'
        ]
        
        all_pricing_items = set()
        
        for selector in pricing_selectors:
            items = soup.select(selector)
            for item in items:
                all_pricing_items.add(item)
        
        print(f"Found {len(all_pricing_items)} unique pricing items")
        
        for item in all_pricing_items:
            try:
                plan_data = self._extract_apex_plan_from_item(item)
                if plan_data and plan_data.get('account_size'):
                    plans.append(plan_data)
                    print(f"Extracted plan: {plan_data.get('account_size', 'Unknown')} {plan_data.get('trial_type', '')} - {plan_data.get('sale_price', 'Unknown')}")
            except Exception as e:
                print(f"Error extracting plan from item: {e}")
                continue
        
        return plans
    
    def _extract_apex_plan_from_item(self, item) -> Dict:
        """Extract plan information from Apex pricing item"""
        plan_data = {}
        
        try:
            # Extract account size and plan type from the h3 tag
            title_element = item.select_one('.pricing__item-top h3')
            if title_element:
                title_text = title_element.get_text(strip=True)
                
                # Extract account size (e.g., "25K FULL", "100K STATIC" -> "25K", "100K")
                account_match = re.search(r'(\d+K)', title_text)
                if account_match:
                    plan_data['account_size'] = f"${account_match.group(1)}"
                
                # Extract plan type (FULL or STATIC)
                if 'FULL' in title_text.upper():
                    plan_data['trial_type'] = 'Full Account'
                elif 'STATIC' in title_text.upper():
                    plan_data['trial_type'] = 'Static Account'
                else:
                    plan_data['trial_type'] = 'Account'
            
            # Extract starting capital from the h6 tag
            capital_element = item.select_one('.pricing__item-top h6')
            if capital_element:
                capital_text = capital_element.get_text(strip=True)
                capital_match = re.search(r'\$([0-9,]+)', capital_text)
                if capital_match:
                    plan_data['starting_capital'] = f"${capital_match.group(1)}"
            
            # Extract details from the pricing list
            list_items = item.select('.pricing__list-item')
            for list_item in list_items:
                text = list_item.get_text(strip=True)
                
                if 'Profit Goal' in text:
                    profit_match = re.search(r'Profit Goal\s+\$([0-9,]+)', text)
                    if profit_match:
                        plan_data['profit_goal'] = f"${profit_match.group(1)}"
                
                elif 'Contracts' in text:
                    contract_match = re.search(r'Contracts\s+(.+)', text)
                    if contract_match:
                        plan_data['contracts'] = contract_match.group(1).strip()
                
                elif 'Trailing Threshold' in text:
                    if 'None' in text:
                        plan_data['trailing_threshold'] = 'None'
                    else:
                        threshold_match = re.search(r'Trailing Threshold\s+\$([0-9,]+)', text)
                        if threshold_match:
                            plan_data['trailing_threshold'] = f"${threshold_match.group(1)}"
                
                elif 'Daily Drawdown' in text:
                    drawdown_match = re.search(r'Daily Drawdown\s+\$([0-9,]+)', text)
                    if drawdown_match:
                        plan_data['daily_drawdown'] = f"${drawdown_match.group(1)}"
            
            # Extract price from the bottom section
            price_element = item.select_one('.pricing__item-bottom p')
            if price_element:
                price_text = price_element.get_text(strip=True)
                price_match = re.search(r'\$(\d+)/Month', price_text)
                if price_match:
                    plan_data['sale_price'] = f"${price_match.group(1)}/Month"
                    plan_data['monthly_price'] = f"${price_match.group(1)}"
            
        except Exception as e:
            print(f"Error extracting from pricing item: {e}")
        
        return plan_data
    
    def get_fallback_plans(self) -> List[Dict]:
        """Apex fallback plans"""
        return [
            {
                'account_size': '$25K',
                'sale_price': '$147/Month',
                'profit_goal': '$1,500',
                'starting_capital': '$25,000',
                'contracts': '4(40 Micros)',
                'trailing_threshold': '$1,500',
                'trial_type': 'Full Account'
            },
            {
                'account_size': '$50K',
                'sale_price': '$167/Month',
                'profit_goal': '$3,000',
                'starting_capital': '$50,000',
                'contracts': '10(100 Micros)',
                'trailing_threshold': '$2,500',
                'trial_type': 'Full Account'
            },
            {
                'account_size': '$100K',
                'sale_price': '$207/Month',
                'profit_goal': '$6,000',
                'starting_capital': '$100,000',
                'contracts': '14(140 Micros)',
                'trailing_threshold': '$3,000',
                'trial_type': 'Full Account'
            },
            {
                'account_size': '$100K',
                'sale_price': '$137/Month',
                'profit_goal': '$2,000',
                'starting_capital': '$100,000',
                'contracts': '2(20 Micros)',
                'trailing_threshold': 'None',
                'daily_drawdown': '$625',
                'trial_type': 'Static Account'
            }
        ]
    
    def get_default_trustpilot_score(self) -> str:
        return "4.5"


# Example implementation for a different trading platform
class TopstepTraderScraper(BaseScraper):
    def __init__(self):
        super().__init__("https://www.topsteptrader.com", "TopstepTrader")
    
    def get_main_urls(self) -> List[str]:
        return [f"{self.base_url}/express-funded-account"]
    
    def extract_plans_from_soup(self, soup: BeautifulSoup, url: str) -> List[Dict]:
        """Extract TopstepTrader-specific pricing plans"""
        plans = []
        
        # TopstepTrader uses different selectors
        plan_elements = soup.select('.plan-card, .pricing-card, [class*="plan"], [class*="pricing"]')
        
        for element in plan_elements:
            try:
                plan_data = {}
                
                # Extract account size
                size_text = self._extract_text_by_selectors(
                    element, 
                    ['h3', '.plan-title', '.account-size', '[class*="size"]']
                )
                if size_text:
                    size_match = re.search(r'\$?(\d+[KM]?)', size_text)
                    if size_match:
                        plan_data['account_size'] = f"${size_match.group(1)}"
                
                # Extract price
                price_text = self._extract_text_by_selectors(
                    element,
                    ['.price', '.cost', '[class*="price"]', '[class*="cost"]']
                )
                if price_text:
                    plan_data['sale_price'] = self._extract_price_from_text(price_text)
                
                # Extract profit goal
                profit_text = element.get_text()
                profit_match = re.search(r'profit.*?\$([0-9,]+)', profit_text, re.IGNORECASE)
                if profit_match:
                    plan_data['profit_goal'] = f"${profit_match.group(1)}"
                
                plan_data['trial_type'] = 'Express Funded Account'
                
                if plan_data.get('account_size') and plan_data.get('sale_price'):
                    plans.append(plan_data)
                    
            except Exception as e:
                print(f"Error extracting TopstepTrader plan: {e}")
                continue
        
        return plans
    
    def get_fallback_plans(self) -> List[Dict]:
        """TopstepTrader fallback plans"""
        return [
            {
                'account_size': '$50K',
                'sale_price': '$165/Month',
                'profit_goal': '$3,000',
                'trial_type': 'Express Funded Account'
            },
            {
                'account_size': '$100K',
                'sale_price': '$325/Month',
                'profit_goal': '$6,000',
                'trial_type': 'Express Funded Account'
            }
        ]


# Multi-scraper manager
class TradingPlatformScraper:
    def __init__(self):
        self.scrapers = [
            ApexTraderFundingScraper(),
            TopstepTraderScraper(),
            # Add more scrapers here
        ]
        self.all_data = []
    
    def scrape_all_platforms(self) -> List[Dict]:
        """Scrape all registered platforms"""
        for scraper in self.scrapers:
            try:
                print(f"\nScraping {scraper.business_name}...")
                plans = scraper.scrape_all()
                standardized_data = scraper.get_standardized_data()
                self.all_data.extend(standardized_data)
                print(f"Scraped {len(standardized_data)} plans from {scraper.business_name}")
            except Exception as e:
                print(f"Error scraping {scraper.business_name}: {e}")
        
        return self.all_data
    
    def save_combined_data(self, filename: str = "all_trading_platforms.csv"):
        """Save all scraped data to a single file"""
        if not self.all_data:
            print("No data to save")
            return
        
        fieldnames = list(self.all_data[0].keys()) if self.all_data else []
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.all_data)
        
        print(f"Combined data saved to {filename}")


# Usage example
def main():
    # Scrape individual platform
    apex_scraper = ApexTraderFundingScraper()
    apex_plans = apex_scraper.scrape_all()
    apex_scraper.print_results()
    apex_scraper.save_to_csv()
    
    # Scrape all platforms
    multi_scraper = TradingPlatformScraper()
    all_data = multi_scraper.scrape_all_platforms()
    multi_scraper.save_combined_data()
    
    print(f"Total plans scraped across all platforms: {len(all_data)}")


if __name__ == "__main__":
    main()
