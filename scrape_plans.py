# scrape_plans.py
# pip install firecrawl pandas pydantic

from firecrawl import FirecrawlApp
from pydantic import BaseModel
from typing import List
import pandas as pd
import re
import os

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

# -----------------------------
# Helper Functions
# -----------------------------
def convert_k_to_thousands(value):
    if not isinstance(value, str):
        return value
    pattern = r'(\d+(?:\.\d+)?)K'
    def replace_k(match):
        num = float(match.group(1)) * 1000
        return f"{int(num):,}" if num.is_integer() else f"{num:,.1f}"
    return re.sub(pattern, replace_k, value, flags=re.IGNORECASE)

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
# Scraping Loop
# -----------------------------
for url in urls:
    print(f"\nScraping {url} ...")
    try:
        # Step 1: Click all tab elements
        app.scrape(
            url=url,
            formats=[],
            only_main_content=False,
            timeout=180000,
            actions={ "click": '[class*="tab"]' }
        )

        # Step 2: Wait 5 seconds for content to load
        app.scrape(
            url=url,
            formats=[],
            only_main_content=False,
            timeout=180000,
            actions={ "wait": 5000 }
        )

        # Step 3: Extract the data according to your schema
        doc = app.scrape(
            url=url,
            formats=[{"type": "json", "schema": ExtractSchema}],
            only_main_content=False,
            timeout=180000
        )

        data = doc.json
        if not data:
            print(f"  No data returned for {url}")
            continue

        # Debug info
        print(f"  Data keys: {list(data.keys())}")

        # Flatten plans
        for plan in data.get("plans", []):
            plan_dict = dict(plan)
            plan_dict["business_name"] = data.get("business_name", "")
            plan_dict["discount_code"] = data.get("discount_code", "")
            plan_dict["trustpilot_score"] = data.get("trustpilot_score", "")
            plan_dict["source_url"] = url

            if "account_size" in plan_dict:
                original = plan_dict["account_size"]
                plan_dict["account_size"] = convert_k_to_thousands(original)
            all_plans.append(plan_dict)

    except Exception as e:
        print(f"  Error scraping {url}: {e}")

# -----------------------------
# Save results
# -----------------------------
if all_plans:
    df = pd.DataFrame(all_plans)
    df.to_csv("plans_output.csv", index=False)
    print(f"\nScraping completed, saved {len(df)} plans to plans_output.csv")
else:
    print("\nNo plans were scraped. CSV not created.")
