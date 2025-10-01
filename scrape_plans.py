# scrape_plans.py

# Imports
from firecrawl import FirecrawlApp
from pydantic import BaseModel
from typing import List
import pandas as pd
import re
import os

# Initialize Firecrawl
api_key = os.getenv("FIRECRAWL_API_KEY")
app = FirecrawlApp(api_key=api_key)

# ---------------------------
# Define Schemas
# ---------------------------
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
    drawdown_mode: str  # New field

class ExtractSchema(BaseModel):
    business_name: str
    discount_code: str
    trustpilot_score: str
    plans: List[Plan]

# ---------------------------
# Helper function to convert K notation
# ---------------------------
def convert_k_to_thousands(value):
    if not isinstance(value, str):
        return value
    pattern = r'(\d+(?:\.\d+)?)K'
    def replace_k(match):
        num_value = float(match.group(1)) * 1000
        return f"{int(num_value):,}" if num_value.is_integer() else f"{num_value:,.1f}"
    return re.sub(pattern, replace_k, value, flags=re.IGNORECASE)

# ---------------------------
# URLs to scrape
# ---------------------------
urls = [
    "https://rightlinefunding.com/",
    "https://tradeify.co/",
    "https://apextraderfunding.com/",
    "https://myfundedfutures.com/",
    "https://thelegendstrading.com/",
    "https://www.topstep.com/",
]

# ---------------------------
# Collect all plan data
# ---------------------------
all_plans = []

for url in urls:
    print(f"Scraping {url} ...")
    try:
        # Scrape the page using Firecrawl
        doc = app.scrape(
            url=url,
            formats=[{
                "type": "json",
                "schema": ExtractSchema
            }],
            only_main_content=False,
            timeout=120000
        )

        # Extract JSON from Document
        data = doc.json()

        if not data:
            print(f"  No data returned for {url}")
            continue

        # Flatten plans with overall metadata
        for plan in data.get("plans", []):
            plan_dict = dict(plan)
            plan_dict["business_name"] = data.get("business_name", "")
            plan_dict["discount_code"] = data.get("discount_code", "")
            plan_dict["trustpilot_score"] = data.get("trustpilot_score", "")
            plan_dict["source_url"] = url

            # Convert account_size K-values
            if "account_size" in plan_dict:
                plan_dict["account_size"] = convert_k_to_thousands(plan_dict["account_size"])

            all_plans.append(plan_dict)

    except Exception as e:
        print(f"  Error scraping {url}: {e}")

# ---------------------------
# Convert to DataFrame and save CSV
# ---------------------------
if all_plans:
    plans_df = pd.DataFrame(all_plans)
    print("\nFirst few rows of scraped data:")
    print(plans_df.head())
    plans_df.to_csv("plans_output.csv", index=False)
    print(f"\nScraping completed, saved {len(plans_df)} plans to plans_output.csv")
else:
    print("No plans were scraped. CSV not created.")
