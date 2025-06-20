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

# Import the base scraper class (assuming it's in the same file or imported)
from BaseScraper import BaseScraper, TradingPlan

class TradeifyScraper(BaseScraper):
    def __init__(self):
        super().__init__("https://tradeify.co", "Tradeify")
    
    def get_main_urls(self) -> List[str]:
        """Return main URLs to scrape for Tradeify"""
        return [
            self.base_url,
            f"{self.base_url}/pricing",
            f"{self.base_url}/plans",
            f"{self.base_url}/accounts"
        ]
    
    def get_additional_urls(self) -> List[str]:
        """Return additional URLs that might contain pricing information"""
        return [
            f"{self.base_url}/straight-to-funded",
            f"{self.base_url}/evaluation-account",
            f"{self.base_url}/sim-funded"
        ]
    
    def extract_plans_from_soup(self, soup: BeautifulSoup, url: str) -> List[Dict]:
        """Extract Tradeify-specific pricing plans from the soup"""
        plans = []
        
        # Primary selectors based on the HTML structure provided
        plan_selectors = [
            '.plan-li .plan',  # Main plan container
            '.plans .plan-li',  # Alternative container
            '[class*="plan-li"]',  # Any element with plan-li in class
            '.c-plans-4 .plan-li'  # Specific plans container
        ]
        
        plan_elements = []
        
        # Collect all unique plan elements
        for selector in plan_selectors:
            elements = soup.select(selector)
            for element in elements:
                if element not in plan_elements:
                    plan_elements.append(element)
        
        print(f"Found {len(plan_elements)} plan elements on {url}")
        
        for element in plan_elements:
            try:
                plan_data = self._extract_tradeify_plan_from_element(element)
                if plan_data and plan_data.get('account_size'):
                    plans.append(plan_data)
                    print(f"Extracted plan: {plan_data.get('account_size', 'Unknown')} - {plan_data.get('sale_price', 'Unknown')}")
            except Exception as e:
                print(f"Error extracting plan from element: {e}")
                continue
        
        # If no plans found with primary selectors, try alternative approaches
        if not plans:
            plans.extend(self._extract_plans_alternative_methods(soup))
        
        return plans
    
    def _extract_tradeify_plan_from_element(self, element) -> Dict:
        """Extract plan information from a Tradeify plan element"""
        plan_data = {}
        
        try:
            # Extract account size from heading
            account_heading = element.select_one('.heading, h4, .plan-header h4')
            if account_heading:
                heading_text = account_heading.get_text(strip=True)
                # Extract account size (e.g., "$25k account" -> "$25K")
                account_match = re.search(r'\$?(\d+[kK])', heading_text)
                if account_match:
                    account_size = account_match.group(1).upper()
                    if not account_size.startswith('$'):
                        account_size = f"${account_size}"
                    plan_data['account_size'] = account_size
            
            # Extract account type
            acc_type_element = element.select_one('.acc-type')
            if acc_type_element:
                acc_type = acc_type_element.get_text(strip=True)
                plan_data['trial_type'] = acc_type
            else:
                plan_data['trial_type'] = 'Funded Account'
            
            # Extract price
            price_element = element.select_one('.price .number')
            if price_element:
                price_text = price_element.get_text(strip=True)
                if price_text and price_text != '$':
                    if not price_text.startswith('$'):
                        price_text = f"${price_text}"
                    plan_data['sale_price'] = price_text
                    
                    # Check if it's one-time fee or monthly
                    period_element = element.select_one('.price .period')
                    if period_element:
                        period_text = period_element.get_text(strip=True)
                        if 'one time' in period_text.lower():
                            plan_data['sale_price'] = f"{price_text} (One-time)"
                        elif 'month' in period_text.lower():
                            plan_data['sale_price'] = f"{price_text}/Month"
            
            # Extract plan attributes
            plan_attributes = element.select('.plan-attr')
            for attr in plan_attributes:
                attr_text = attr.get_text(strip=True)
                
                if 'Max Contracts' in attr_text:
                    contract_match = re.search(r'Max Contracts:\s*(.+)', attr_text)
                    if contract_match:
                        plan_data['max_contracts'] = contract_match.group(1).strip()
                
                elif 'Daily Loss Limit' in attr_text:
                    if 'None' in attr_text:
                        plan_data['daily_loss_limit'] = 'None'
                    else:
                        loss_match = re.search(r'Daily Loss Limit.*?\$([0-9,]+)', attr_text)
                        if loss_match:
                            plan_data['daily_loss_limit'] = f"${loss_match.group(1)}"
                
                elif 'Trailing Max Drawdown' in attr_text:
                    drawdown_match = re.search(r'Trailing Max Drawdown:\s*\$([0-9,]+)', attr_text)
                    if drawdown_match:
                        plan_data['trailing_drawdown'] = f"${drawdown_match.group(1)}"
                
                elif 'Drawdown Mode' in attr_text:
                    mode_match = re.search(r'Drawdown Mode:\s*(.+)', attr_text)
                    if mode_match:
                        plan_data['drawdown_mode'] = mode_match.group(1).strip()
                
                elif 'Min Trading Days' in attr_text:
                    days_match = re.search(r'Min Trading Days.*?(\d+)', attr_text)
                    if days_match:
                        plan_data['min_trading_days'] = days_match.group(1)
                
                elif 'Consistency' in attr_text:
                    consistency_match = re.search(r'Consistency:\s*(\d+%?)', attr_text)
                    if consistency_match:
                        plan_data['consistency'] = consistency_match.group(1)
                        if not consistency_match.group(1).endswith('%'):
                            plan_data['consistency'] += '%'
                
                elif 'Max Accounts' in attr_text:
                    accounts_match = re.search(r'Max Accounts:\s*(\d+)', attr_text)
                    if accounts_match:
                        plan_data['max_accounts'] = accounts_match.group(1)
                
                elif 'Profit Goal' in attr_text or 'Target' in attr_text:
                    profit_match = re.search(r'\$([0-9,]+)', attr_text)
                    if profit_match:
                        plan_data['profit_goal'] = f"${profit_match.group(1)}"
            
            # Set funded full price (same as sale price for funded accounts)
            if plan_data.get('sale_price'):
                plan_data['funded_full_price'] = plan_data['sale_price']
        
        except Exception as e:
            print(f"Error extracting from plan element: {e}")
        
        return plan_data
    
    def _extract_plans_alternative_methods(self, soup: BeautifulSoup) -> List[Dict]:
        """Alternative extraction methods if primary selectors fail"""
        plans = []
        
        try:
            # Look for any pricing tables or cards
            pricing_elements = soup.select('[class*="price"], [class*="plan"], [class*="account"]')
            
            for element in pricing_elements:
                text = element.get_text()
                
                # Look for account size patterns
                account_matches = re.findall(r'\$(\d+[kK])', text)
                price_matches = re.findall(r'\$(\d+(?:,\d{3})*)', text)
                
                if account_matches and price_matches:
                    for account in account_matches:
                        for price in price_matches:
                            if account != price:  # Don't match account size with itself
                                plan_data = {
                                    'account_size': f"${account.upper()}",
                                    'sale_price': f"${price}",
                                    'trial_type': 'Funded Account'
                                }
                                plans.append(plan_data)
                                break
        except Exception as e:
            print(f"Error in alternative extraction: {e}")
        
        return plans
    
    def get_fallback_plans(self) -> List[Dict]:
        """Tradeify fallback plans based on common industry standards"""
        return [
            {
                'account_size': '$25K',
                'sale_price': '$349 (One-time)',
                'funded_full_price': '$349 (One-time)',
                'trial_type': 'Straight to Sim Funded',
                'max_contracts': '1 Minis (10 Micros)',
                'daily_loss_limit': 'None',
                'trailing_drawdown': '$1,000',
                'drawdown_mode': 'End Of Day',
                'min_trading_days': '10',
                'consistency': '20%',
                'max_accounts': '5',
                'profit_goal': '$1,500'
            },
            {
                'account_size': '$50K',
                'sale_price': '$449 (One-time)',
                'funded_full_price': '$449 (One-time)',
                'trial_type': 'Straight to Sim Funded',
                'max_contracts': '2 Minis (20 Micros)',
                'daily_loss_limit': 'None',
                'trailing_drawdown': '$2,000',
                'drawdown_mode': 'End Of Day',
                'min_trading_days': '10',
                'consistency': '20%',
                'max_accounts': '5',
                'profit_goal': '$3,000'
            },
            {
                'account_size': '$100K',
                'sale_price': '$649 (One-time)',
                'funded_full_price': '$649 (One-time)',
                'trial_type': 'Straight to Sim Funded',
                'max_contracts': '4 Minis (40 Micros)',
                'daily_loss_limit': 'None',
                'trailing_drawdown': '$4,000',
                'drawdown_mode': 'End Of Day',
                'min_trading_days': '10',
                'consistency': '20%',
                'max_accounts': '5',
                'profit_goal': '$6,000'
            },
            {
                'account_size': '$150K',
                'sale_price': '$849 (One-time)',
                'funded_full_price': '$849 (One-time)',
                'trial_type': 'Straight to Sim Funded',
                'max_contracts': '6 Minis (60 Micros)',
                'daily_loss_limit': 'None',
                'trailing_drawdown': '$6,000',
                'drawdown_mode': 'End Of Day',
                'min_trading_days': '10',
                'consistency': '20%',
                'max_accounts': '5',
                'profit_goal': '$9,000'
            }
        ]
    
    def get_default_trustpilot_score(self) -> str:
        """Default Trustpilot score for Tradeify"""
        return "4.2"
    
    def process_plan_data(self, plan_data: Dict) -> Dict:
        """Process and clean Tradeify plan data"""
        # Clean up account size format
        if plan_data.get('account_size'):
            account_size = plan_data['account_size']
            if 'k' in account_size.lower() and '$' in account_size:
                # Convert $25k to $25K
                plan_data['account_size'] = account_size.upper()
        
        # Ensure consistent price format
        if plan_data.get('sale_price') and not plan_data['sale_price'].startswith('$'):
            plan_data['sale_price'] = f"${plan_data['sale_price']}"
        
        # Set default values for missing fields
        if not plan_data.get('trial_type'):
            plan_data['trial_type'] = 'Funded Account'
        
        return plan_data


# Usage example for Tradeify
def main_tradeify():
    """Example usage of the Tradeify scraper"""
    print("Starting Tradeify scraper...")
    
    # Initialize the scraper
    tradeify_scraper = TradeifyScraper()
    
    # Scrape all plans
    plans = tradeify_scraper.scrape_all()
    
    # Print results
    tradeify_scraper.print_results()
    
    # Save to files
    tradeify_scraper.save_to_csv("tradeify_plans.csv")
    tradeify_scraper.save_to_json("tradeify_plans.json")
    
    print(f"Scraping complete! Found {len(plans)} plans from Tradeify")
    
    return plans


# Extended multi-scraper that includes Tradeify
class ExtendedTradingPlatformScraper:
    def __init__(self):
        self.scrapers = [
            ApexTraderFundingScraper(),
            TopstepTraderScraper(),
            TradeifyScraper(),  # Add Tradeify scraper
            # Add more scrapers here
        ]
        self.all_data = []
    
    def scrape_all_platforms(self) -> List[Dict]:
        """Scrape all registered platforms including Tradeify"""
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
    
    def save_combined_data(self, filename: str = "all_trading_platforms_with_tradeify.csv"):
        """Save all scraped data including Tradeify to a single file"""
        if not self.all_data:
            print("No data to save")
            return
        
        fieldnames = list(self.all_data[0].keys()) if self.all_data else []
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(self.all_data)
        
        print(f"Combined data saved to {filename}")


if __name__ == "__main__":
    # Test just Tradeify
    main_tradeify()
    
    # Or test all platforms including Tradeify
    # multi_scraper = ExtendedTradingPlatformScraper()
    # all_data = multi_scraper.scrape_all_platforms()
    # multi_scraper.save_combined_data()
    # print(f"Total plans scraped across all platforms: {len(all_data)}")
