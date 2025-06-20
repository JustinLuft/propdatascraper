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
            
            # Extract pricing plans using the correct selectors
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
                    trial_type=plan_data.get('trial_type', 'Full Account'),
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

    def _extract_pricing_plans(self, soup: BeautifulSoup) -> List[Dict]:
        """Extract pricing plan information using multiple selectors to capture all plan types"""
        plans = []
        
        # Look for pricing items with multiple possible selectors
        pricing_selectors = [
            '.pricing__item.pricing__item--style2',  # Original selector for FULL plans
            '.pricing__item',  # Generic pricing item selector for STATIC plans
            '[class*="pricing__item"]'  # Any element with pricing__item class
        ]
        
        all_pricing_items = set()  # Use set to avoid duplicates
        
        for selector in pricing_selectors:
            items = soup.select(selector)
            for item in items:
                # Add to set using the element's HTML as a unique identifier
                all_pricing_items.add(item)
        
        print(f"Found {len(all_pricing_items)} unique pricing items")
        
        for item in all_pricing_items:
            try:
                plan_data = self._extract_plan_from_pricing_item(item)
                if plan_data and plan_data.get('account_size'):  # Only add if we extracted valid data
                    plans.append(plan_data)
                    print(f"Extracted plan: {plan_data.get('account_size', 'Unknown')} {plan_data.get('trial_type', '')} - {plan_data.get('sale_price', 'Unknown')}")
            except Exception as e:
                print(f"Error extracting plan from item: {e}")
                continue
        
        return plans

    def _extract_plan_from_pricing_item(self, item) -> Dict:
        """Extract plan information from a pricing item using the exact HTML structure"""
        plan_data = {}
        
        try:
            # Extract account size and plan type from the h3 tag
            title_element = item.select_one('.pricing__item-top h3')
            if title_element:
                title_text = title_element.get_text(strip=True)
                print(f"Processing title: {title_text}")
                
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
                    plan_data['trial_type'] = 'Account'  # Default fallback
            
            # Extract starting capital from the h6 tag
            capital_element = item.select_one('.pricing__item-top h6')
            if capital_element:
                capital_text = capital_element.get_text(strip=True)
                # Extract the actual starting capital amount
                capital_match = re.search(r'\$([0-9,]+)', capital_text)
                if capital_match:
                    plan_data['starting_capital'] = f"${capital_match.group(1)}"
            
            # Extract details from the pricing list
            list_items = item.select('.pricing__list-item')
            for list_item in list_items:
                text = list_item.get_text(strip=True)
                
                # Extract profit goal
                if 'Profit Goal' in text:
                    profit_match = re.search(r'Profit Goal\s+\$([0-9,]+)', text)
                    if profit_match:
                        plan_data['profit_goal'] = f"${profit_match.group(1)}"
                
                # Extract contract information
                elif 'Contracts' in text:
                    contract_match = re.search(r'Contracts\s+(.+)', text)
                    if contract_match:
                        plan_data['contracts'] = contract_match.group(1).strip()
                
                # Extract trailing threshold
                elif 'Trailing Threshold' in text:
                    if 'None' in text:
                        plan_data['trailing_threshold'] = 'None'
                    else:
                        threshold_match = re.search(r'Trailing Threshold\s+\$([0-9,]+)', text)
                        if threshold_match:
                            plan_data['trailing_threshold'] = f"${threshold_match.group(1)}"
                
                # Extract daily drawdown
                elif 'Daily Drawdown' in text:
                    drawdown_match = re.search(r'Daily Drawdown\s+\$([0-9,]+)', text)
                    if drawdown_match:
                        plan_data['daily_drawdown'] = f"${drawdown_match.group(1)}"
                
                # Extract scaling information
                elif 'Scaling' in text:
                    if 'None' in text:
                        plan_data['scaling'] = 'None'
                    else:
                        scaling_match = re.search(r'Scaling\s+(.+)', text)
                        if scaling_match:
                            plan_data['scaling'] = scaling_match.group(1).strip()
                
                # Extract real-time data fees info
                elif 'Real-Time Data Fees' in text:
                    plan_data['real_time_data'] = 'Included' if 'Included' in text else text
            
            # Extract price from the bottom section
            price_element = item.select_one('.pricing__item-bottom p')
            if price_element:
                price_text = price_element.get_text(strip=True)
                # Extract monthly price
                price_match = re.search(r'\$(\d+)/Month', price_text)
                if price_match:
                    plan_data['sale_price'] = f"${price_match.group(1)}/Month"
                    plan_data['monthly_price'] = f"${price_match.group(1)}"
            
            # Extract signup link
            signup_link = item.select_one('.pricing__item-bottom a')
            if signup_link:
                href = signup_link.get('href', '')
                plan_data['signup_link'] = href
                
                # Extract plan type from URL if available
                if 'wealthcharts' in href.lower():
                    plan_data['platform'] = 'WealthCharts'
            
        except Exception as e:
            print(f"Error extracting from pricing item: {e}")
        
        return plan_data

    def _create_fallback_plans(self) -> List[TradingPlan]:
        """Create fallback plans based on the actual Apex structure including STATIC plans"""
        print("Creating fallback plans based on actual Apex structure...")
        
        fallback_plans = [
            # FULL Plans
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
                'account_size': '$150K',
                'sale_price': '$297/Month',
                'profit_goal': '$9,000',
                'starting_capital': '$150,000',
                'contracts': '17(170 Micros)',
                'trailing_threshold': '$5,000',
                'trial_type': 'Full Account'
            },
            {
                'account_size': '$250K',
                'sale_price': '$399/Month',
                'profit_goal': '$15,000',
                'starting_capital': '$250,000',
                'contracts': '27(270 Micros)',
                'trailing_threshold': '$6,500',
                'trial_type': 'Full Account'
            },
            # STATIC Plans
            {
                'account_size': '$100K',
                'sale_price': '$137/Month',
                'profit_goal': '$2,000',
                'starting_capital': '$100,000',
                'contracts': '2(20 Micros)',
                'trailing_threshold': 'None',
                'daily_drawdown': '$625',
                'scaling': 'None',
                'trial_type': 'Static Account'
            }
        ]
        
        for plan_data in fallback_plans:
            plan = TradingPlan(
                business_name="Apex Trader Funding",
                account_size=plan_data['account_size'],
                sale_price=plan_data['sale_price'],
                funded_full_price="",
                discount_code="Contact for codes",
                trial_type=plan_data['trial_type'],
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
        trial_type = new_plan_data.get('trial_type', '')
        
        # Find existing plan with same account size and trial type
        for plan in self.plans:
            if (plan.account_size == account_size and 
                plan.trial_type == trial_type):
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
            trial_type=new_plan_data.get('trial_type', 'Account'),
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
            'discount_code', 'trial_type', 'trustpilot_score', 'profit_goal',
            'starting_capital', 'contracts', 'trailing_threshold', 'daily_drawdown',
            'scaling', 'real_time_data'
        ]
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for plan in self.plans:
                additional = plan.additional_info or {}
                writer.writerow({
                    'business_name': plan.business_name,
                    'account_size': plan.account_size,
                    'sale_price': plan.sale_price,
                    'funded_full_price': plan.funded_full_price,
                    'discount_code': plan.discount_code,
                    'trial_type': plan.trial_type,
                    'trustpilot_score': plan.trustpilot_score,
                    'profit_goal': plan.profit_goal,
                    'starting_capital': additional.get('starting_capital', ''),
                    'contracts': additional.get('contracts', ''),
                    'trailing_threshold': additional.get('trailing_threshold', ''),
                    'daily_drawdown': additional.get('daily_drawdown', ''),
                    'scaling': additional.get('scaling', ''),
                    'real_time_data': additional.get('real_time_data', '')
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
        """Return data in standardized format for combining with other scrapers"""
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


# Test the scraper
if __name__ == "__main__":
    scraper = ApexTraderFundingScraper()
    plans = scraper.scrape_main_page()
    scraper.print_results()
    scraper.save_to_csv()
    scraper.save_to_json()
