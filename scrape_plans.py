# Install Firecrawl
# Imports
from firecrawl import JsonConfig, FirecrawlApp
from pydantic import BaseModel
from typing import List
import pandas as pd
import re

# Initialize Firecrawl
import os
api_key = os.getenv("FIRECRAWL_API_KEY")
app = FirecrawlApp(api_key=api_key)

# Define the schema for each plan
class Plan(BaseModel):
    plan_name: str
    account_type: str
    account_size: str
    price_raw: str
    profit_goal: str
    trailing_drawdown: str
    daily_loss_limit: str
    activation_fee: str
    reset_fee: str
    drawdown_mode: str  # <-- New field added here

# Define the overall schema including multiple plans
class ExtractSchema(BaseModel):
    business_name: str
    discount_code: str
    trustpilot_score: str
    plans: List[Plan]

# Function to convert K notation to full numbers
def convert_k_to_thousands(value):
    """
    Convert values like '50K' to '50,000'
    Handles various formats and preserves currency symbols
    """
    if not isinstance(value, str):
        return value
    
    # Pattern to match numbers followed by K (case insensitive)
    # This preserves any currency symbols or other text
    pattern = r'(\d+(?:\.\d+)?)K'
    
    def replace_k(match):
        number = match.group(1)
        # Convert to float, multiply by 1000, then format with commas
        num_value = float(number) * 1000
        # Format as integer if it's a whole number, otherwise keep decimal
        if num_value.is_integer():
            return f"{int(num_value):,}"
        else:
            return f"{num_value:,.1f}"
    
    # Replace all occurrences of the pattern
    result = re.sub(pattern, replace_k, value, flags=re.IGNORECASE)
    return result

# Create JSON extraction config
json_config = JsonConfig(
    schema=ExtractSchema
)

# List of URLs to scrape
urls = [
    "https://tradeify.co/plan",
    "https://apextraderfunding.com/",
    "https://myfundedfutures.com/",
    "https://thelegendstrading.com/",
    "https://www.topstep.com/",
    # Add more URLs here
    # "https://anotherwebsite.com/plans",
]

# Collect all scraped plan data here
all_plans = []

for url in urls:
    print(f"Scraping {url} ...")
    try:
        response = app.scrape_url(
            url=url,
            formats=["json"],
            json_options=json_config,
            only_main_content=False,
            timeout=120000
        )
        data = response.json
        
        # Flatten and enrich each plan with overall metadata
        for plan in data.get('plans', []):
            plan_dict = dict(plan)
            plan_dict['business_name'] = data.get('business_name', '')
            plan_dict['discount_code'] = data.get('discount_code', '')
            plan_dict['trustpilot_score'] = data.get('trustpilot_score', '')
            plan_dict['source_url'] = url  # Optional: keep track of source
            
            # Convert K notation in account_size field
            if 'account_size' in plan_dict:
                original_value = plan_dict['account_size']
                converted_value = convert_k_to_thousands(original_value)
                plan_dict['account_size'] = converted_value
                
                # Optional: Print conversion for debugging
                if original_value != converted_value:
                    print(f"  Converted account_size: '{original_value}' -> '{converted_value}'")
            
            all_plans.append(plan_dict)
            
    except Exception as e:
        print(f"Error scraping {url}: {e}")

# Convert all collected plans to a single DataFrame
plans_df = pd.DataFrame(all_plans)

# Display top rows
print("\nFirst few rows of scraped data:")
print(plans_df.head())

# Save to CSV file
plans_df.to_csv("plans_output.csv", index=False)
print(f"\nScraping completed, saved plans_output.csv with {len(plans_df)} plans")

# Optional: Show any account_size values that were converted
if len(plans_df) > 0 and 'account_size' in plans_df.columns:
    print(f"\nAccount size values found:")
    for idx, size in enumerate(plans_df['account_size'].unique()):
        if pd.notna(size):
            print(f"  {size}")
