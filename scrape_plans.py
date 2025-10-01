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
# JavaScript to intelligently find and click tabs
# -----------------------------
click_all_tabs_script = """
(function() {
    const clicked = new Set();
    const clicks = [];
    
    // Helper to click element and track it
    function clickElement(el) {
        if (!el || clicked.has(el)) return false;
        
        try {
            // Scroll into view
            el.scrollIntoView({ behavior: 'smooth', block: 'center' });
            
            // Wait a moment for scroll
            setTimeout(() => {
                el.click();
                clicked.add(el);
                console.log('Clicked:', el.textContent?.trim() || el.className);
            }, 100);
            
            return true;
        } catch(e) {
            console.log('Click failed:', e);
            return false;
        }
    }
    
    // Strategy 1: Find buttons with role="tab"
    document.querySelectorAll('button[role="tab"], a[role="tab"]').forEach(el => {
        if (clickElement(el)) clicks.push('role-tab');
    });
    
    // Strategy 2: Find elements with "tab" in class name
    document.querySelectorAll('[class*="tab" i]').forEach(el => {
        if ((el.tagName === 'BUTTON' || el.tagName === 'A') && 
            el.offsetParent !== null) { // is visible
            if (clickElement(el)) clicks.push('class-tab');
        }
    });
    
    // Strategy 3: Find buttons with data-tab attribute
    document.querySelectorAll('[data-tab], [data-tabs]').forEach(el => {
        if (clickElement(el)) clicks.push('data-tab');
    });
    
    // Strategy 4: Look for plan/pricing related text in buttons/links
    const planKeywords = ['core', 'scale', 'pro', 'basic', 'advanced', 'premium', 
                          'starter', 'growth', 'lightning', '25k', '50k', '100k', '150k'];
    
    document.querySelectorAll('button, a').forEach(el => {
        const text = el.textContent?.toLowerCase() || '';
        const hasKeyword = planKeywords.some(kw => text.includes(kw));
        
        if (hasKeyword && el.offsetParent !== null && text.length < 50) {
            if (clickElement(el)) clicks.push('keyword-match');
        }
    });
    
    // Strategy 5: Find sibling buttons that look like tabs (grouped buttons)
    const buttonGroups = new Map();
    document.querySelectorAll('button').forEach(btn => {
        if (btn.offsetParent === null) return; // skip hidden
        const parent = btn.parentElement;
        if (!buttonGroups.has(parent)) {
            buttonGroups.set(parent, []);
        }
        buttonGroups.get(parent).push(btn);
    });
    
    buttonGroups.forEach((buttons, parent) => {
        // If parent has 2-5 buttons, they're likely tabs
        if (buttons.length >= 2 && buttons.length <= 5) {
            buttons.forEach(btn => {
                if (clickElement(btn)) clicks.push('button-group');
            });
        }
    });
    
    console.log('Total click strategies used:', [...new Set(clicks)]);
    console.log('Total unique elements clicked:', clicked.size);
    
    return {
        clicked: clicked.size,
        strategies: [...new Set(clicks)]
    };
})();
"""

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
# Scraping Loop with intelligent tab detection
# -----------------------------
for url in urls:
    print(f"\nScraping {url} ...")
    try:
        # Scrape with dynamic JavaScript-based clicking
        doc = app.scrape(
            url=url,
            formats=[{"type": "json", "schema": ExtractSchema}],
            only_main_content=False,
            timeout=120000,
            actions=[
                {
                    "type": "execute",
                    "script": click_all_tabs_script
                },
                {
                    "type": "wait",
                    "milliseconds": 2000  # Wait for content to load after all clicks
                }
            ]
        )

        data = doc.json
        if not data:
            print(f"  No data returned for {url}")
            continue

        # Debug: show keys
        print(f"  Data type: {type(data)}")
        if isinstance(data, dict):
            print(f"  Data keys: {list(data.keys())}")
            print(f"  Found {len(data.get('plans', []))} plans")

        # Flatten plans and enrich with metadata
        for plan in data.get("plans", []):
            plan_dict = dict(plan)
            plan_dict["business_name"] = data.get("business_name", "")
            plan_dict["discount_code"] = data.get("discount_code", "")
            plan_dict["trustpilot_score"] = data.get("trustpilot_score", "")
            plan_dict["source_url"] = url

            if "account_size" in plan_dict:
                original_value = plan_dict["account_size"]
                plan_dict["account_size"] = convert_k_to_thousands(original_value)
                if original_value != plan_dict["account_size"]:
                    print(f"  Converted account_size: '{original_value}' -> '{plan_dict['account_size']}'")
            else:
                print(f"  Warning: account_size missing for plan '{plan_dict.get('plan_name','?')}'")

            all_plans.append(plan_dict)

    except Exception as e:
        print(f"  Error scraping {url}: {e}")
        import traceback
        traceback.print_exc()

# -----------------------------
# Save results
# -----------------------------
if all_plans:
    plans_df = pd.DataFrame(all_plans)
    plans_df.to_csv("plans_output.csv", index=False)
    print(f"\nScraping completed, saved plans_output.csv with {len(plans_df)} plans")

    # Show breakdown by site
    print("\nPlans found per site:")
    for url in urls:
        count = len([p for p in all_plans if p.get("source_url") == url])
        business_name = next((p.get("business_name") for p in all_plans if p.get("source_url") == url), "Unknown")
        print(f"  {business_name}: {count} plans ({url})")

    # Optional: show unique account sizes
    if 'account_size' in plans_df.columns:
        print("\nAccount size values found:")
        for size in sorted(plans_df['account_size'].dropna().unique()):
            print(f"  {size}")
else:
    print("\nNo plans were scraped. CSV not created.")
