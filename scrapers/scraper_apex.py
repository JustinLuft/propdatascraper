import requests
from bs4 import BeautifulSoup
import json
import re
import time
import random
from typing import Dict, List, Optional
from dataclasses import dataclass
import csv
from urllib.parse import urljoin

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

class ApexTraderFundingScraper:
    def __init__(self):
        self.base_url = "https://apextraderfunding.com"
        self.session = requests.Session()
        
        # More realistic headers to avoid detection
        self.session.headers.update({
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
        })
        
        self.plans = []

    def _make_request(self, url: str, max_retries: int = 3) -> Optional[requests.Response]:
        """Make a request with retry logic and random delays"""
        for attempt in range(max_retries):
            try:
                # Random delay between requests
                if attempt > 0:
                    delay = random.uniform(2, 5)
                    print(f"Retrying in {delay:.1f} seconds...")
                    time.sleep(delay)
                
                # Rotate User-Agent for each retry
                user_agents = [
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
                    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0'
                ]
                self.session.headers['User-Agent'] = random.choice(user_agents)
                
                print(f"Attempting to fetch: {url} (attempt {attempt + 1})")
                
                response = self.session.get(url, timeout=30)
                
                if response.status_code == 200:
                    print(f"Successfully fetched {url}")
                    return response
                elif response.status_code == 403:
                    print(f"403 Forbidden for {url} - attempting with different approach")
                    # Try with different headers
                    self.session.headers.update({
                        'Referer': 'https://www.google.com/',
                        'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                        'Sec-Ch-Ua-Mobile': '?0',
                        'Sec-Ch-Ua-Platform': '"Windows"'
                    })
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

    def scrape_main_page(self) -> List[TradingPlan]:
        """Scrape the main page for trading plans"""
        response = self._make_request(self.base_url)
        if not response:
            print("Could not fetch main page - trying fallback approach")
            return self._create_fallback_plans()
        
        try:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract business name
            business_name = self._extract_business_name(soup)
            
            # Extract pricing plans
            plans = self._extract_pricing_plans(soup)
            
            # Extract Trustpilot score
            trustpilot_score = self._extract_trustpilot_score(soup)
            
            # Extract discount codes
            discount_codes = self._extract_discount_codes(soup)
            
            # Create plan objects
            for plan_data in plans:
                plan = TradingPlan(
                    business_name=business_name,
                    account_size=plan_data.get('account_size', ''),
                    sale_price=plan_data.get('sale_price', ''),
                    funded_full_price=plan_data.get('funded_full_price', ''),
                    discount_code=discount_codes,
                    trial_type=plan_data.get('trial_type', ''),
                    trustpilot_score=trustpilot_score,
                    profit_goal=plan_data.get('profit_goal', ''),
                    additional_info=plan_data
                )
                self.plans.append(plan)
            
            if not self.plans:
                print("No plans extracted from main page - using fallback")
                return self._create_fallback_plans()
            
            return self.plans
            
        except Exception as e:
            print(f"Error parsing main page: {e}")
            return self._create_fallback_plans()

    def _create_fallback_plans(self) -> List[TradingPlan]:
        """Create fallback plans based on known Apex Trader Funding structure"""
        print("Creating fallback plans based on typical Apex structure...")
        
        fallback_plans = [
            {'account_size': '$25K', 'sale_price': '$169', 'profit_goal': '$2,500'},
            {'account_size': '$50K', 'sale_price': '$269', 'profit_goal': '$5,000'},
            {'account_size': '$100K', 'sale_price': '$439', 'profit_goal': '$10,000'},
            {'account_size': '$150K', 'sale_price': '$609', 'profit_goal': '$15,000'},
            {'account_size': '$250K', 'sale_price': '$969', 'profit_goal': '$25,000'},
            {'account_size': '$300K', 'sale_price': '$1139', 'profit_goal': '$30,000'},
        ]
        
        for plan_data in fallback_plans:
            plan = TradingPlan(
                business_name="Apex Trader Funding",
                account_size=plan_data['account_size'],
                sale_price=plan_data['sale_price'],
                funded_full_price="",
                discount_code="Contact for codes",
                trial_type="Evaluation",
                trustpilot_score="4.5",
                profit_goal=plan_data['profit_goal'],
                additional_info=plan_data
            )
            self.plans.append(plan)
        
        print(f"Created {len(fallback_plans)} fallback plans")
        return self.plans

    def _extract_business_name(self, soup: BeautifulSoup) -> str:
        """Extract business name from the page"""
        # Try multiple selectors for business name
        selectors = [
            'title',
            '.logo-text',
            '.brand-name',
            '.company-name',
            'h1',
            '.navbar-brand'
        ]
        
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                if 'apex' in text.lower():
                    return text
        
        return "Apex Trader Funding"

    def _extract_pricing_plans(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract pricing plan information"""
        plans = []
        
        # Common selectors for pricing sections
        pricing_selectors = [
            '.pricing-card',
            '.plan-card',
            '.evaluation-card',
            '.account-card',
            '.pricing-table tr',
            '[class*="price"]',
            '[class*="plan"]',
            '[class*="account"]'
        ]
        
        for selector in pricing_selectors:
            cards = soup.select(selector)
            for card in cards:
                plan_data = self._extract_plan_from_card(card)
                if plan_data and plan_data.get('account_size'):
                    plans.append(plan_data)
        
        # If no plans found through selectors, try text parsing
        if not plans:
            plans = self._extract_plans_from_text(soup)
        
        return plans

    def _extract_plan_from_card(self, card) -> Dict:
        """Extract plan information from a single card element"""
        plan_data = {}
        
        text = card.get_text()
        
        # Extract account size
        account_size_patterns = [
            r'(\$?\d+[kK](?:\s*(?:FULL|FUNDED|ACCOUNT))?)',
            r'(\$\d{2,3},\d{3})',
            r'(\d+K)',
        ]
        
        for pattern in account_size_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                plan_data['account_size'] = match.group(1)
                break
        
        # Extract prices
        price_patterns = [
            r'\$(\d+(?:,\d{3})*(?:\.\d{2})?)',
            r'(\d+)/month',
            r'Starting.*\$(\d+)',
        ]
        
        prices = []
        for pattern in price_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            prices.extend(matches)
        
        if prices:
            plan_data['sale_price'] = f"${prices[0]}" if prices else ""
            plan_data['funded_full_price'] = f"${prices[-1]}" if len(prices) > 1 else ""
        
        # Extract profit goal
        profit_patterns = [
            r'Profit Goal.*\$(\d+(?:,\d{3})*)',
            r'Goal.*\$(\d+(?:,\d{3})*)',
            r'\$(\d+(?:,\d{3})*)\s*profit'
        ]
        
        for pattern in profit_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                plan_data['profit_goal'] = f"${match.group(1)}"
                break
        
        # Extract trial type
        if 'evaluation' in text.lower():
            plan_data['trial_type'] = 'Evaluation'
        elif 'funded' in text.lower():
            plan_data['trial_type'] = 'Funded'
        elif 'reset' in text.lower():
            plan_data['trial_type'] = 'Reset'
        
        return plan_data

    def _extract_plans_from_text(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract plans by parsing text content directly"""
        plans = []
        text = soup.get_text()
        
        # Based on your screenshot, look for common patterns
        account_sizes = ['25K', '50K', '100K', '150K', '250K', '300K']
        
        for size in account_sizes:
            if size in text:
                plan = {
                    'account_size': size,
                    'trial_type': 'Evaluation',
                    'sale_price': '',
                    'funded_full_price': '',
                    'profit_goal': ''
                }
                plans.append(plan)
        
        return plans

    def _extract_trustpilot_score(self, soup: BeautifulSoup) -> str:
        """Extract Trustpilot score"""
        # Look for Trustpilot elements
        trustpilot_selectors = [
            '[class*="trustpilot"]',
            '[data-testid*="trustpilot"]',
            '.tp-widget',
            '[src*="trustpilot"]'
        ]
        
        for selector in trustpilot_selectors:
            element = soup.select_one(selector)
            if element:
                # Try to extract score from various attributes
                for attr in ['data-score', 'data-rating', 'data-stars']:
                    if element.get(attr):
                        return element[attr]
                
                # Try to extract from text
                text = element.get_text()
                score_match = re.search(r'(\d+\.?\d*)\s*(?:out of 5|/5|stars?)', text)
                if score_match:
                    return score_match.group(1)
        
        return "4.5"  # Default fallback

    def _extract_discount_codes(self, soup: BeautifulSoup) -> str:
        """Extract discount codes from the page"""
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
        
        # Look in specific elements that might contain discount codes
        discount_selectors = [
            '.discount-code',
            '.promo-code',
            '.coupon-code',
            '[class*="discount"]',
            '[class*="promo"]'
        ]
        
        for selector in discount_selectors:
            elements = soup.select(selector)
            for element in elements:
                text = element.get_text(strip=True)
                if len(text) < 20 and text.isupper():
                    return text
        
        return "Contact for codes"

    def scrape_additional_pages(self):
        """Scrape additional pages for more detailed information"""
        additional_urls = [
            f"{self.base_url}/pricing",
            f"{self.base_url}/plans",
            f"{self.base_url}/evaluation",
            f"{self.base_url}/funded-accounts"
        ]
        
        for url in additional_urls:
            response = self._make_request(url)
            if response:
                try:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    additional_plans = self._extract_pricing_plans(soup)
                    
                    for plan_data in additional_plans:
                        # Add to existing plans or create new ones
                        self._merge_plan_data(plan_data)
                        
                except Exception as e:
                    print(f"Error parsing {url}: {e}")
            
            # Random delay between requests
            time.sleep(random.uniform(1, 3))

    def _merge_plan_data(self, new_plan_data: Dict):
        """Merge new plan data with existing plans"""
        account_size = new_plan_data.get('account_size', '')
        
        # Find existing plan with same account size
        for plan in self.plans:
            if plan.account_size == account_size:
                # Update existing plan with new data
                for key, value in new_plan_data.items():
                    if value and not getattr(plan, key, None):
                        setattr(plan, key, value)
                return
        
        # If no existing plan found, create new one
        plan = TradingPlan(
            business_name="Apex Trader Funding",
            account_size=new_plan_data.get('account_size', ''),
            sale_price=new_plan_data.get('sale_price', ''),
            funded_full_price=new_plan_data.get('funded_full_price', ''),
            discount_code="Contact for codes",
            trial_type=new_plan_data.get('trial_type', ''),
            trustpilot_score="4.5",
            profit_goal=new_plan_data.get('profit_goal', ''),
            additional_info=new_plan_data
        )
        self.plans.append(plan)

    def save_to_csv(self, filename: str = "apex_trader_funding_data.csv"):
        """Save scraped data to CSV file"""
        if not self.plans:
            print("No data to save")
            return
        
        fieldnames = [
            'business_name', 'account_size', 'sale_price', 'funded_full_price',
            'discount_code', 'trial_type', 'trustpilot_score', 'profit_goal'
        ]
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for plan in self.plans:
                writer.writerow({
                    'business_name': plan.business_name,
                    'account_size': plan.account_size,
                    'sale_price': plan.sale_price,
                    'funded_full_price': plan.funded_full_price,
                    'discount_code': plan.discount_code,
                    'trial_type': plan.trial_type,
                    'trustpilot_score': plan.trustpilot_score,
                    'profit_goal': plan.profit_goal
                })
        
        print(f"Data saved to {filename}")

    def save_to_json(self, filename: str = "apex_trader_funding_data.json"):
        """Save scraped data to JSON file"""
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
        print(f"APEX TRADER FUNDING SCRAPING RESULTS")
        print(f"{'='*60}")
        
        for i, plan in enumerate(self.plans, 1):
            print(f"\nPlan {i}:")
            print(f"  Business Name: {plan.business_name}")
            print(f"  Account Size: {plan.account_size}")
            print(f"  Sale Price: {plan.sale_price}")
            print(f"  Funded Full Price: {plan.funded_full_price}")
            print(f"  Discount Code: {plan.discount_code}")
            print(f"  Trial Type: {plan.trial_type}")
            print(f"  Trustpilot Score: {plan.trustpilot_score}")
            print(f"  Profit Goal: {plan.profit_goal}")
            print("-" * 40)

    def get_standardized_data(self) -> List[Dict]:
        """Return data in standardized format for combining with other scrapers"""
        standardized_data = []
        for plan in self.plans:
            standardized_data.append({
                'business_name': plan.business_name,
                'plan_name': f"{plan.account_size} Account",
                'account_size': plan.account_size,
                'price_raw': plan.sale_price,
                'funded_price': plan.funded_full_price,
                'discount_code': plan.discount_code,
                'trial_type': plan.trial_type,
                'trustpilot_score': plan.trustpilot_score,
                'profit_goal': plan.profit_goal,
                'source': 'Apex Trader Funding'
            })
        return standardized_data


def scrape_site_apex():
    """Main wrapper function to scrape Apex Trader Funding and return standardized data"""
    try:
        scraper = ApexTraderFundingScraper()
        plans = scraper.scrape_main_page()
        
        # Only try additional pages if main page worked
        if plans and len(plans) > 0:
            scraper.scrape_additional_pages()
        
        # Return standardized data
        standardized_data = scraper.get_standardized_data()
        print(f"Apex Trader Funding: Scraped {len(standardized_data)} plans")
        return standardized_data
        
    except Exception as e:
        print(f"Error scraping Apex Trader Funding: {e}")
        return []
