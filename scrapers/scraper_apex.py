import requests
from bs4 import BeautifulSoup
import json
import re
import time
from typing import Dict, List, Optional
from dataclasses import dataclass
import csv

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
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        self.plans = []

    def scrape_main_page(self) -> List[TradingPlan]:
        """Scrape the main page for trading plans"""
        try:
            response = self.session.get(self.base_url)
            response.raise_for_status()
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
            
            return self.plans
            
        except requests.RequestException as e:
            print(f"Error fetching main page: {e}")
            return []

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
        
        return "Not available"

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
        
        return "No code available"

    def scrape_additional_pages(self):
        """Scrape additional pages for more detailed information"""
        additional_urls = [
            f"{self.base_url}/pricing",
            f"{self.base_url}/plans",
            f"{self.base_url}/evaluation",
            f"{self.base_url}/funded-accounts"
        ]
        
        for url in additional_urls:
            try:
                response = self.session.get(url)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, 'html.parser')
                    additional_plans = self._extract_pricing_plans(soup)
                    
                    for plan_data in additional_plans:
                        # Add to existing plans or create new ones
                        self._merge_plan_data(plan_data)
                        
            except requests.RequestException as e:
                print(f"Error fetching {url}: {e}")
                continue
            
            time.sleep(1)  # Be respectful with requests

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
            discount_code="",
            trial_type=new_plan_data.get('trial_type', ''),
            trustpilot_score="",
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
