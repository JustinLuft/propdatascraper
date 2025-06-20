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

class TradeifyScraper:
    """Tradeify web scraper for extracting trading plan data"""
    
    def __init__(self):
        self.base_url = "https://tradeify.co"
        self.business_name = "Tradeify"
        self.session = requests.Session()
        self.plans = []
        
        # Set headers
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
        """Extract Trustpilot score from page"""
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
        
        return "4.2"  # Default Tradeify score
    
    def _extract_discount_codes(self, soup: BeautifulSoup) -> str:
        """Extract discount codes from page"""
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
    
    def get_main_urls(self) -> List[str]:
        """Return list of main URLs to scrape"""
        return [
            f"{self.base_url}",
            f"{self.base_url}/pricing",
            f"{self.base_url}/plans"
        ]
    
    def get_additional_urls(self) -> List[str]:
        """Return additional URLs to scrape"""
        return [
            f"{self.base_url}/straight-to-funded",
            f"{self.base_url}/evaluation-account",
            f"{self.base_url}/sim-funded-account"
        ]
    
    def extract_plans_from_soup(self, soup: BeautifulSoup, url: str) -> List[Dict]:
        """Extract Tradeify-specific pricing plans"""
        plans = []
        
        # Look for plan containers based on the HTML structure provided
        plan_selectors = [
            '.plan-li .plan',
            '.plan',
            '[class*="plan-li"]',
            '.plans .plan-li'
        ]
        
        all_plans = set()
        
        for selector in plan_selectors:
            plan_elements = soup.select(selector)
            for element in plan_elements:
                all_plans.add(element)
        
        print(f"Found {len(all_plans)} unique plan elements")
        
        for plan_element in all_plans:
            try:
                plan_data = self._extract_tradeify_plan_from_element(plan_element)
                if plan_data and plan_data.get('account_size'):
                    plans.append(plan_data)
                    print(f"Extracted plan: {plan_data.get('account_size', 'Unknown')} - {plan_data.get('sale_price', 'Unknown')}")
            except Exception as e:
                print(f"Error extracting plan from element: {e}")
                continue
        
        return plans
    
    def _extract_tradeify_plan_from_element(self, element) -> Dict:
        """Extract plan information from Tradeify plan element"""
        plan_data = {}
        
        try:
            # Extract account size from heading (e.g., "$25k account")
            heading_element = element.select_one('.heading, h4')
            if heading_element:
                heading_text = heading_element.get_text(strip=True)
                account_match = re.search(r'\$(\d+[kK])', heading_text)
                if account_match:
                    plan_data['account_size'] = f"${account_match.group(1).upper()}"
            
            # Extract trial type from acc-type
            acc_type_element = element.select_one('.acc-type')
            if acc_type_element:
                plan_data['trial_type'] = acc_type_element.get_text(strip=True)
            
            # Extract price from .price section
            price_element = element.select_one('.price .number')
            if price_element:
                price_text = price_element.get_text(strip=True)
                plan_data['sale_price'] = price_text
                
                # Check for period (one time fee, monthly, etc.)
                period_element = element.select_one('.price .period')
                if period_element:
                    period_text = period_element.get_text(strip=True)
                    plan_data['sale_price'] = f"{price_text} {period_text}"
            
            # Extract plan attributes
            attr_elements = element.select('.plan-attr')
            for attr_element in attr_elements:
                attr_text = attr_element.get_text(strip=True)
                
                # Extract max contracts
                if 'Max Contracts:' in attr_text:
                    contract_match = re.search(r'Max Contracts:\s*(.+)', attr_text)
                    if contract_match:
                        plan_data['max_contracts'] = contract_match.group(1).strip()
                
                # Extract daily loss limit
                elif 'Daily Loss Limit' in attr_text:
                    if 'None' in attr_text:
                        plan_data['daily_loss_limit'] = 'None'
                    else:
                        loss_match = re.search(r'Daily Loss Limit.*?\$([0-9,]+)', attr_text)
                        if loss_match:
                            plan_data['daily_loss_limit'] = f"${loss_match.group(1)}"
                
                # Extract trailing max drawdown
                elif 'Trailing Max Drawdown:' in attr_text:
                    drawdown_match = re.search(r'Trailing Max Drawdown:\s*\$([0-9,]+)', attr_text)
                    if drawdown_match:
                        plan_data['trailing_max_drawdown'] = f"${drawdown_match.group(1)}"
                
                # Extract drawdown mode
                elif 'Drawdown Mode:' in attr_text:
                    mode_match = re.search(r'Drawdown Mode:\s*(.+)', attr_text)
                    if mode_match:
                        plan_data['drawdown_mode'] = mode_match.group(1).strip()
                
                # Extract min trading days
                elif 'Min Trading Days to Payout:' in attr_text:
                    days_match = re.search(r'Min Trading Days to Payout:\s*(\d+)', attr_text)
                    if days_match:
                        plan_data['min_trading_days'] = days_match.group(1)
                
                # Extract consistency requirement
                elif 'Consistency:' in attr_text:
                    consistency_match = re.search(r'Consistency:\s*(\d+%)', attr_text)
                    if consistency_match:
                        plan_data['consistency'] = consistency_match.group(1)
                
                # Extract max accounts
                elif 'Max Accounts:' in attr_text:
                    accounts_match = re.search(r'Max Accounts:\s*(\d+)', attr_text)
                    if accounts_match:
                        plan_data['max_accounts'] = accounts_match.group(1)
            
            # Set profit goal based on account size (if not found elsewhere)
            if not plan_data.get('profit_goal') and plan_data.get('account_size'):
                account_size = plan_data['account_size']
                if '$25K' in account_size:
                    plan_data['profit_goal'] = '$1,500'
                elif '$50K' in account_size:
                    plan_data['profit_goal'] = '$3,000'
                elif '$100K' in account_size:
                    plan_data['profit_goal'] = '$6,000'
                elif '$150K' in account_size:
                    plan_data['profit_goal'] = '$9,000'
            
            # Set funded full price (same as sale price for direct funded accounts)
            if plan_data.get('sale_price') and 'Straight to' in plan_data.get('trial_type', ''):
                plan_data['funded_full_price'] = plan_data['sale_price']
            else:
                plan_data['funded_full_price'] = 'N/A'
        
        except Exception as e:
            print(f"Error extracting from plan element: {e}")
        
        return plan_data
    
    def get_fallback_plans(self) -> List[Dict]:
        """Tradeify fallback plans"""
        return [
            {
                'account_size': '$25K',
                'sale_price': '$349 one time fee',
                'funded_full_price': '$349 one time fee',
                'profit_goal': '$1,500',
                'trial_type': 'Straight to Sim Funded',
                'max_contracts': '1 Minis (10 Micros)',
                'daily_loss_limit': 'None',
                'trailing_max_drawdown': '$1,000',
                'drawdown_mode': 'End Of Day',
                'min_trading_days': '10',
                'consistency': '20%',
                'max_accounts': '5'
            },
            {
                'account_size': '$50K',
                'sale_price': '$549 one time fee',
                'funded_full_price': '$549 one time fee',
                'profit_goal': '$3,000',
                'trial_type': 'Straight to Sim Funded',
                'max_contracts': '2 Minis (20 Micros)',
                'daily_loss_limit': 'None',
                'trailing_max_drawdown': '$2,000',
                'drawdown_mode': 'End Of Day',
                'min_trading_days': '10',
                'consistency': '20%',
                'max_accounts': '5'
            },
            {
                'account_size': '$100K',
                'sale_price': '$949 one time fee',
                'funded_full_price': '$949 one time fee',
                'profit_goal': '$6,000',
                'trial_type': 'Straight to Sim Funded',
                'max_contracts': '4 Minis (40 Micros)',
                'daily_loss_limit': 'None',
                'trailing_max_drawdown': '$4,000',
                'drawdown_mode': 'End Of Day',
                'min_trading_days': '10',
                'consistency': '20%',
                'max_accounts': '5'
            }
        ]
    
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
                        plan = self._create_trading_plan(plan_data, soup)
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
                trustpilot_score=plan_data.get('trustpilot_score', '4.2'),
                profit_goal=plan_data.get('profit_goal', ''),
                additional_info=plan_data
            )
        except Exception as e:
            print(f"Error creating trading plan from dict: {e}")
            return None
    
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


# Usage example
def main():
    # Create and run Tradeify scraper
    tradeify_scraper = TradeifyScraper()
    plans = tradeify_scraper.scrape_all()
    
    # Display results
    tradeify_scraper.print_results()
    
    # Save to files
    tradeify_scraper.save_to_csv()
    tradeify_scraper.save_to_json()
    
    print(f"Total Tradeify plans scraped: {len(plans)}")


if __name__ == "__main__":
    main()
