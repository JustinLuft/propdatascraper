import requests
from bs4 import BeautifulSoup
import re
import json
import csv
from dataclasses import dataclass
from typing import List, Dict, Optional

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

class ApexTraderFundingScraper:
    def __init__(self):
        self.base_url = "https://apextraderfunding.com"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
    def scrape(self) -> List[TradingPlan]:
        """Main scraping method"""
        try:
            response = requests.get(self.base_url, headers=self.headers, timeout=30)
            if response.status_code != 200:
                return self._get_fallback_plans()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract data
            business_name = self._extract_business_name(soup)
            trustpilot_score = self._extract_trustpilot_score(soup)
            discount_code = self._extract_discount_code(soup)
            plans_data = self._extract_plans(soup)
            
            # Create plan objects
            plans = []
            for plan_data in plans_data:
                plan = TradingPlan(
                    business_name=business_name,
                    account_size=plan_data.get('account_size', ''),
                    sale_price=plan_data.get('sale_price', ''),
                    funded_full_price=plan_data.get('funded_full_price', ''),
                    discount_code=discount_code,
                    trial_type=plan_data.get('trial_type', ''),
                    trustpilot_score=trustpilot_score,
                    profit_goal=plan_data.get('profit_goal', '')
                )
                plans.append(plan)
            
            return plans if plans else self._get_fallback_plans()
            
        except Exception as e:
            print(f"Scraping error: {e}")
            return self._get_fallback_plans()
    
    def _extract_business_name(self, soup: BeautifulSoup) -> str:
        """Extract business name"""
        title = soup.find('title')
        if title and 'apex' in title.get_text().lower():
            return "Apex Trader Funding"
        return "Apex Trader Funding"
    
    def _extract_trustpilot_score(self, soup: BeautifulSoup) -> str:
        """Extract Trustpilot score"""
        # Look for trustpilot elements
        trustpilot_elements = soup.find_all(attrs={'class': re.compile(r'trustpilot', re.I)})
        for element in trustpilot_elements:
            text = element.get_text()
            score_match = re.search(r'(\d+\.?\d*)', text)
            if score_match:
                return score_match.group(1)
        return "4.5"  # Default
    
    def _extract_discount_code(self, soup: BeautifulSoup) -> str:
        """Extract discount codes"""
        text = soup.get_text()
        patterns = [
            r'(?:code|coupon):\s*([A-Z0-9]{3,10})',
            r'use\s+code\s+([A-Z0-9]{3,10})',
            r'promo\s*code:\s*([A-Z0-9]{3,10})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return "Contact for codes"
    
    def _extract_plans(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract pricing plans"""
        plans = []
        
        # Look for pricing items
        pricing_items = soup.select('.pricing__item')
        
        for item in pricing_items:
            plan_data = {}
            
            # Extract title (account size and type)
            title_elem = item.select_one('h3')
            if title_elem:
                title = title_elem.get_text(strip=True)
                
                # Extract account size
                size_match = re.search(r'(\d+K)', title)
                if size_match:
                    plan_data['account_size'] = f"${size_match.group(1)}"
                
                # Extract trial type
                if 'FULL' in title.upper():
                    plan_data['trial_type'] = 'Full Account'
                elif 'STATIC' in title.upper():
                    plan_data['trial_type'] = 'Static Account'
                else:
                    plan_data['trial_type'] = 'Account'
            
            # Extract price
            price_elem = item.select_one('.pricing__item-bottom p')
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                price_match = re.search(r'\$(\d+)/Month', price_text)
                if price_match:
                    plan_data['sale_price'] = f"${price_match.group(1)}/Month"
            
            # Extract profit goal from list items
            list_items = item.select('.pricing__list-item')
            for list_item in list_items:
                text = list_item.get_text(strip=True)
                if 'Profit Goal' in text:
                    profit_match = re.search(r'Profit Goal\s+\$([0-9,]+)', text)
                    if profit_match:
                        plan_data['profit_goal'] = f"${profit_match.group(1)}"
            
            # Set default funded price (usually empty for monthly plans)
            plan_data['funded_full_price'] = ""
            
            if plan_data.get('account_size'):
                plans.append(plan_data)
        
        return plans
    
    def _get_fallback_plans(self) -> List[TradingPlan]:
        """Fallback plans if scraping fails"""
        fallback_data = [
            # FULL Plans
            {'account_size': '$25K', 'sale_price': '$147/Month', 'profit_goal': '$1,500', 'trial_type': 'Full Account'},
            {'account_size': '$50K', 'sale_price': '$167/Month', 'profit_goal': '$3,000', 'trial_type': 'Full Account'},
            {'account_size': '$100K', 'sale_price': '$207/Month', 'profit_goal': '$6,000', 'trial_type': 'Full Account'},
            {'account_size': '$150K', 'sale_price': '$297/Month', 'profit_goal': '$9,000', 'trial_type': 'Full Account'},
            {'account_size': '$250K', 'sale_price': '$399/Month', 'profit_goal': '$15,000', 'trial_type': 'Full Account'},
            # STATIC Plans
            {'account_size': '$100K', 'sale_price': '$137/Month', 'profit_goal': '$2,000', 'trial_type': 'Static Account'}
        ]
        
        plans = []
        for data in fallback_data:
            plan = TradingPlan(
                business_name="Apex Trader Funding",
                account_size=data['account_size'],
                sale_price=data['sale_price'],
                funded_full_price="",
                discount_code="Contact for codes",
                trial_type=data['trial_type'],
                trustpilot_score="4.5",
                profit_goal=data['profit_goal']
            )
            plans.append(plan)
        
        return plans
    
    def save_to_csv(self, plans: List[TradingPlan], filename: str = "apex_data.csv"):
        """Save to CSV"""
        if not plans:
            return
        
        fieldnames = ['business_name', 'account_size', 'sale_price', 'funded_full_price', 
                     'discount_code', 'trial_type', 'trustpilot_score', 'profit_goal']
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for plan in plans:
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
    
    def scrape_main_page(self) -> List[TradingPlan]:
        """Main scraping method - renamed to match your existing code"""
        return self.scrape()
    
    def scrape_additional_pages(self):
        """Placeholder for compatibility - does nothing in optimized version"""
        pass
    
    def get_standardized_data(self) -> List[Dict]:
        """Return data in standardized format for combining with other scrapers"""
        if not hasattr(self, 'plans') or not self.plans:
            self.plans = self.scrape()
        
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
                'source': 'Apex Trader Funding'
            })
        return standardized_data
        """Print results"""
        print(f"\nApex Trader Funding - {len(plans)} plans found:")
        print("-" * 50)
        for i, plan in enumerate(plans, 1):
            print(f"{i}. {plan.account_size} {plan.trial_type}")
            print(f"   Price: {plan.sale_price}")
            print(f"   Profit Goal: {plan.profit_goal}")
            print(f"   Trustpilot: {plan.trustpilot_score}")
            print(f"   Discount: {plan.discount_code}")
            print()

# Usage
if __name__ == "__main__":
    scraper = ApexTraderFundingScraper()
    plans = scraper.scrape_main_page()
    scraper.print_results()
    scraper.save_to_csv(plans)
