# scrape_plans.py
# pip install firecrawl pandas pydantic

from firecrawl import FirecrawlApp
from pydantic import BaseModel
from typing import List
import pandas as pd
import re
import os
import json

# -----------------------------
# Initialize Firecrawl
# -----------------------------
api_key = os.getenv("FIRECRAWL_API_KEY")
app = FirecrawlApp(api_key=api_key)

# -----------------------------
# Define Schemas
# -----------------------------
class Plan(BaseModel):
    plan_name: str
    account_type: str
    account_size: str
    price_raw: str
    profit_goal: str
    drawdown_type: str  # e.g., "Intraday Trailing", "End of Day", etc.
    drawdown: str  # The actual drawdown amount, e.g., "$2,000"
    daily_loss_limit: str
    activation_fee: str
    reset_fee: str

class ExtractSchema(BaseModel):
    business_name: str
    discount_code: str
    trustpilot_score: str
    plans: List[Plan]

# -----------------------------
# Helper Functions
# -----------------------------
def convert_k_to_thousands(value):
    """Convert '50K' -> '50,000', preserving currency symbols."""
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

def clean_drawdown_fields(plan_dict):
    """
    Ensure drawdown and drawdown_type are properly separated.
    drawdown should contain the numeric value, drawdown_type should contain the type.
    """
    # If drawdown contains non-numeric text like "Trailing" or "Intraday Trailing",
    # it's probably the type, not the value
    if "drawdown" in plan_dict:
        drawdown_val = str(plan_dict.get("drawdown", ""))
        # Check if it contains only descriptive text (no currency symbol or significant numbers)
        if drawdown_val and not re.search(r'[\$€£¥]|\d{3,}', drawdown_val):
            # This is likely a type, not a value
            if not plan_dict.get("drawdown_type"):
                plan_dict["drawdown_type"] = drawdown_val
            plan_dict["drawdown"] = ""
    
    # Ensure empty strings for missing values
    if not plan_dict.get("drawdown"):
        plan_dict["drawdown"] = ""
    if not plan_dict.get("drawdown_type"):
        plan_dict["drawdown_type"] = ""
    
    return plan_dict

# -----------------------------
# URLs to scrape
# -----------------------------
urls = [
    "https://rightlinefunding.com/",
    "https://tradeify.co/",
    "https://apextraderfunding.com/",
    "https://myfundedfutures.com/",
    "https://thelegendstrading.com/",
    "https://www.topstep.com/",
]

all_plans = []

# -----------------------------
# Scraping Loop with detailed debug
# -----------------------------
for url in urls:
    print(f"\nScraping {url} ...")
    try:
        doc = app.scrape(
            url=url,
            formats=[{
                "type": "json",
                "schema": ExtractSchema
            }],
            only_main_content=False,
            timeout=120000
        )

        # doc.json is a property, not callable
        data = doc.json

        if not data:
            print(f"  No data returned for {url}")
            continue

        # Debug: print type & keys
        print(f"  Data type: {type(data)}")
        if isinstance(data, dict):
            print(f"  Data keys: {list(data.keys())}")
            for key, value in list(data.items())[:3]:
                preview = str(value)[:50] if value else "None"
                print(f"    {key}: {preview}...")
        else:
            print(f"  Data preview: {str(data)[:200]}...")

        # Flatten plans and enrich with metadata
        for plan in data.get("plans", []):
            plan_dict = dict(plan)
            plan_dict["business_name"] = data.get("business_name", "")
            plan_dict["discount_code"] = data.get("discount_code", "")
            plan_dict["trustpilot_score"] = data.get("trustpilot_score", "")
            plan_dict["source_url"] = url

            # Convert K notation
            if "account_size" in plan_dict:
                original_value = plan_dict["account_size"]
                plan_dict["account_size"] = convert_k_to_thousands(original_value)
                if original_value != plan_dict["account_size"]:
                    print(f"  Converted account_size: '{original_value}' -> '{plan_dict['account_size']}'")

            # Clean drawdown fields
            plan_dict = clean_drawdown_fields(plan_dict)
            
            # Rename drawdown to trailing_drawdown for CSV output
            if "drawdown" in plan_dict:
                plan_dict["trailing_drawdown"] = plan_dict.pop("drawdown")

            all_plans.append(plan_dict)

    except Exception as e:
        print(f"  Error scraping {url}: {e}")
        try:
            print(f"    doc type: {type(doc)}")
            print(f"    doc attributes: {dir(doc)}")
        except:
            pass

# -----------------------------
# Save results
# -----------------------------
if all_plans:
    plans_df = pd.DataFrame(all_plans)
    plans_df.to_csv("plans_output.csv", index=False)
    print(f"\nScraping completed, saved plans_output.csv with {len(plans_df)} plans")

    # Optional: show unique account sizes
    if 'account_size' in plans_df.columns:
        print("\nAccount size values found:")
        for size in plans_df['account_size'].dropna().unique():
            print(f"  {size}")
else:
    print("\nNo plans were scraped. CSV not created.")
