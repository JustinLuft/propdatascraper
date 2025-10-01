# scrape_plans.py

# Imports
import os
import re
import pandas as pd
from pydantic import BaseModel
from typing import List
from firecrawl import Firecrawl

# Initialize Firecrawl
api_key = os.getenv("FIRECRAWL_API_KEY")
if not api_key:
    raise ValueError("Please set the FIRECRAWL_API_KEY environment variable.")
app = Firecrawl(api_key=api_key)

# -------------------------
# Define schema
# -------------------------
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
    drawdown_mode: str

class ExtractSchema(BaseModel):
    business_name: str
    discount_code: str
    trustpilot_score: str
    plans: List[Plan]

# -------------------------
# Helper function: K notation
# -------------------------
def convert_k_to_thousands(value):
    """
    Converts '50K' -> '50,000' and preserves other text/currency
    """
    if not isinstance(value, str):
        return value

    pattern = r'(\d+(?:\.\d+)?)K'

    def replace_k(match):
        number = match.group(1)
        num_value = float(number) * 1000
        return f"{int(num_value):,}" if num_value.is_integer() else f"{num_value:,.1f}"

    return re.sub(pattern, replace_k, value, flags=re.IGNORECASE)

# -------------------------
# URLs to scrape
# -------------------------
urls = [
    "https://rightlinefunding.com/",
    "https://tradeify.co/",
    "https://apextraderfunding.com/",
    "https://myfundedfutures.com/",
    "https://thelegendstrading.com/",
    "https://www.topstep.com/",
]

# -------------------------
# Main scraping loop
# -------------------------
all_plans = []

for url in urls:
    print(f"Scraping {url} ...")
    try:
        response = app.scrape(
            url=url,
            json={
                "type": "json",
                "prompt": (
                    "Extract all plan details, including plan name, account type, account size, "
                    "price, profit goal, trailing drawdown, daily loss limit, activation fee, reset fee, "
                    "drawdown mode, as well as business name, discount code, and trustpilot score."
                ),
                "schema": ExtractSchema
            },
            only_main_content=False,
            timeout=120000
        )

        data = response.get("json", {})
        if data:
            for plan in data.get('plans', []):
                plan_dict = dict(plan)
                # Add metadata
                plan_dict['business_name'] = data.get('business_name', '')
                plan_dict['discount_code'] = data.get('discount_code', '')
                plan_dict['trustpilot_score'] = data.get('trustpilot_score', '')
                plan_dict['source_url'] = url
                # Convert account_size K-values
                if 'account_size' in plan_dict:
                    plan_dict['account_size'] = convert_k_to_thousands(plan_dict['account_size'])
                all_plans.append(plan_dict)
    except Exception as e:
        print(f"Error scraping {url}: {e}")

# -------------------------
# Save to CSV
# -------------------------
plans_df = pd.DataFrame(all_plans)

if len(plans_df) > 0:
    plans_df.to_csv("plans_output.csv", index=False)
    print(f"\nScraping completed, saved plans_output.csv with {len(plans_df)} plans")
else:
    print("\nNo plans were scraped. CSV not created.")
