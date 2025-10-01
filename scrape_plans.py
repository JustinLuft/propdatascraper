# scrape_plans.py

# Imports
from firecrawl import JsonConfig, FirecrawlApp
from pydantic import BaseModel
from typing import List
import pandas as pd
import re
import os
import json

# Initialize Firecrawl
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
    drawdown_mode: str

# Define the overall schema including multiple plans
class ExtractSchema(BaseModel):
    business_name: str
    discount_code: str
    trustpilot_score: str
    plans: List[Plan]

# Convert K notation to full numbers
def convert_k_to_thousands(value):
    if not isinstance(value, str):
        return value
    pattern = r'(\d+(?:\.\d+)?)K'
    def replace_k(match):
        number = match.group(1)
        num_value = float(number) * 1000
        if num_value.is_integer():
            return f"{int(num_value):,}"
        else:
            return f"{num_value:,.1f}"
    return re.sub(pattern, replace_k, value, flags=re.IGNORECASE)

# Config for JSON extraction
json_config = JsonConfig(schema=ExtractSchema)

# List of URLs to scrape
urls = [
    "https://rightlinefunding.com/",
    "https://tradeify.co/",
    "https://apextraderfunding.com/",
    "https://myfundedfutures.com/",
    "https://thelegendstrading.com/",
    "https://www.topstep.com/",
]

all_plans = []

for url in urls:
    print(f"Scraping {url} ...")
    try:
        response = app.extract(
            url=url,
            config=json_config,
            only_main_content=False,
            timeout=120000
        )

        parsed_response = response.model_dump()  # dict

        if parsed_response and "plans" in parsed_response:
            data = parsed_response
            print(f"  Found {len(data['plans'])} plans for {url}")

            for plan in data.get("plans", []):
                plan_dict = dict(plan)
                plan_dict["business_name"] = data.get("business_name", "")
                plan_dict["discount_code"] = data.get("discount_code", "")
                plan_dict["trustpilot_score"] = data.get("trustpilot_score", "")
                plan_dict["source_url"] = url

                if "account_size" in plan_dict:
                    original_value = plan_dict["account_size"]
                    converted_value = convert_k_to_thousands(original_value)
                    plan_dict["account_size"] = converted_value
                    if original_value != converted_value:
                        print(f"    Converted account_size: '{original_value}' -> '{converted_value}'")

                all_plans.append(plan_dict)
        else:
            print(f"  No plans found for {url}")

    except Exception as e:
        print(f"Error scraping {url}: {e}")

# Save results
plans_df = pd.DataFrame(all_plans)
print("\nFirst few rows of scraped data:")
print(plans_df.head())

plans_df.to_csv("plans_output.csv", index=False)
print(f"\nScraping completed, saved plans_output.csv with {len(plans_df)} plans")
