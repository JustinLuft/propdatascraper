# Install Firecrawl

# Imports
from firecrawl import JsonConfig, FirecrawlApp
from pydantic import BaseModel
from typing import List
import pandas as pd

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

# Create JSON extraction config
json_config = JsonConfig(
    schema=ExtractSchema
)

# List of URLs to scrape
urls = [
    "https://tradeify.co/plan",
    "https://apextraderfunding.com/",   # Add more URLs here
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

            all_plans.append(plan_dict)

    except Exception as e:
        print(f"Error scraping {url}: {e}")

# Convert all collected plans to a single DataFrame
plans_df = pd.DataFrame(all_plans)

# Display top rows
print(plans_df.head())

# Convert all collected plans to a single DataFrame
plans_df = pd.DataFrame(all_plans)

# Save to CSV file
plans_df.to_csv("plans_output.csv", index=False)

print("Scraping completed, saved plans_output.csv")

