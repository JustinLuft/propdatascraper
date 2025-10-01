# scrape_plans.py
# pip install firecrawl pandas pydantic

from firecrawl import FirecrawlApp
from pydantic import BaseModel
from typing import List
import pandas as pd
import re
import os
import json
import time

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

# -----------------------------
# Site configurations with multiple scrapes per site
# Each site can have multiple "passes" to click different tabs
# -----------------------------
sites_config = [
    {
        "name": "Right Line Funding",
        "url": "https://rightlinefunding.com/",
        "passes": [
            {"description": "Default view", "actions": None},
        ]
    },
    {
        "name": "Tradeify",
        "url": "https://tradeify.co/",
        "passes": [
            {"description": "Lightning Funded", "actions": None},
            {"description": "Growth tab", "actions": [
                {"type": "click", "selector": "button:has-text('Growth'), a:has-text('Growth')"},
                {"type": "wait", "milliseconds": 2000}
            ]},
            {"description": "Advanced tab", "actions": [
                {"type": "click", "selector": "button:has-text('Advanced'), a:has-text('Advanced')"},
                {"type": "wait", "milliseconds": 2000}
            ]},
        ]
    },
    {
        "name": "Apex Trader Funding",
        "url": "https://apextraderfunding.com/",
        "passes": [
            {"description": "Default view", "actions": None},
        ]
    },
    {
        "name": "MyFunded Futures",
        "url": "https://myfundedfutures.com/",
        "passes": [
            {"description": "Core plan", "actions": None},
            {"description": "Scale plan", "actions": [
                {"type": "click", "selector": "button:nth-of-type(2)"},
                {"type": "wait", "milliseconds": 2000}
            ]},
            {"description": "Pro plan", "actions": [
                {"type": "click", "selector": "button:nth-of-type(3)"},
                {"type": "wait", "milliseconds": 2000}
            ]},
        ]
    },
    {
        "name": "The Legends Trading",
        "url": "https://thelegendstrading.com/",
        "passes": [
            {"description": "Default view", "actions": None},
        ]
    },
    {
        "name": "TopStep",
        "url": "https://www.topstep.com/",
        "passes": [
            {"description": "Default view", "actions": None},
        ]
    },
]

all_plans = []
seen_plans = set()  # Track unique plans to avoid duplicates

# -----------------------------
# Scraping Loop
# -----------------------------
for site_config in sites_config:
    site_name = site_config["name"]
    url = site_config["url"]
    passes = site_config["passes"]
    
    print(f"\n{'='*60}")
    print(f"Scraping {site_name} ({url})")
    print(f"{'='*60}")
    
    site_plans_count = 0
    
    for pass_idx, pass_config in enumerate(passes):
        description = pass_config["description"]
        actions = pass_config["actions"]
        
        print(f"\n  Pass {pass_idx + 1}/{len(passes)}: {description}")
        
        try:
            # Scrape with or without actions
            doc = app.scrape(
                url=url,
                formats=[{"type": "json", "schema": ExtractSchema}],
                only_main_content=False,
                timeout=120000,
                actions=actions if actions else []
            )

            data = doc.json
            if not data:
                print(f"    No data returned")
                continue

            # Extract plans
            plans = data.get('plans', [])
            print(f"    Found {len(plans)} plans in this pass")

            # Process plans
            for plan in plans:
                # Create unique identifier for deduplication
                plan_id = f"{url}|{plan.get('plan_name', '')}|{plan.get('account_size', '')}|{plan.get('price_raw', '')}"
                
                if plan_id in seen_plans:
                    print(f"      Skipping duplicate: {plan.get('plan_name', 'Unknown')}")
                    continue
                
                seen_plans.add(plan_id)
                
                plan_dict = dict(plan)
                plan_dict["business_name"] = data.get("business_name", site_name)
                plan_dict["discount_code"] = data.get("discount_code", "")
                plan_dict["trustpilot_score"] = data.get("trustpilot_score", "")
                plan_dict["source_url"] = url

                # Convert K notation
                if "account_size" in plan_dict:
                    original_value = plan_dict["account_size"]
                    plan_dict["account_size"] = convert_k_to_thousands(original_value)

                all_plans.append(plan_dict)
                site_plans_count += 1
                
                print(f"      ✓ {plan.get('plan_name', 'Unknown')}: {plan_dict.get('account_size', '?')} (${plan.get('price_raw', '?')})")
            
            # Small delay between passes
            if pass_idx < len(passes) - 1:
                time.sleep(1)

        except Exception as e:
            print(f"    ✗ Error in pass: {e}")
    
    print(f"\n  Total plans from {site_name}: {site_plans_count}")
    time.sleep(2)  # Delay between sites

# -----------------------------
# Save results
# -----------------------------
print(f"\n{'='*60}")
if all_plans:
    plans_df = pd.DataFrame(all_plans)
    plans_df.to_csv("plans_output.csv", index=False)
    print(f"✓ SUCCESS! Saved plans_output.csv with {len(plans_df)} plans")
    print(f"{'='*60}")

    # Show breakdown by site
    print("\n📊 Summary by Site:")
    print("-" * 60)
    for site_config in sites_config:
        site_name = site_config["name"]
        url = site_config["url"]
        site_plans = [p for p in all_plans if p.get("source_url") == url]
        count = len(site_plans)
        print(f"\n{site_name}: {count} plans")
        if site_plans:
            for p in site_plans:
                plan_name = p.get('plan_name', '?')
                account_size = p.get('account_size', '?')
                price = p.get('price_raw', '?')
                print(f"  • {plan_name}: {account_size} @ ${price}")

    # Show unique account sizes
    if 'account_size' in plans_df.columns:
        print(f"\n📈 All Unique Account Sizes:")
        print("-" * 60)
        unique_sizes = sorted(plans_df['account_size'].dropna().unique())
        for size in unique_sizes:
            count = len(plans_df[plans_df['account_size'] == size])
            print(f"  {size}: {count} plans")
else:
    print("✗ No plans were scraped.")
    print(f"{'='*60}")
