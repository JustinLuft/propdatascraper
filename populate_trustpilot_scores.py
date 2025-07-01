import pandas as pd
import time
import re
import os
from firecrawl import FirecrawlApp

# Initialize Firecrawl with API key from environment variable
api_key = os.getenv("FIRECRAWL_API_KEY")
app = FirecrawlApp(api_key=api_key)

# Load existing CSV
csv_path = "plans_output.csv"
df = pd.read_csv(csv_path)

# Function to get Trustpilot score
def get_trustpilot_score(business_name: str) -> str:
    try:
        print(f"🔍 Searching for: {business_name}")
        query = f"site:trustpilot.com {business_name}"
        search_response = app.search(query=query)  # FIXED: removed num_results

        if not search_response.results:
            print(f"❌ No Trustpilot result found for: {business_name}")
            return "Not found"

        trustpilot_url = search_response.results[0].url
        print(f"🔗 Trustpilot URL found: {trustpilot_url}")

        page = app.scrape_url(
            url=trustpilot_url,
            formats=["text"],
            only_main_content=False,
            timeout=90000
        )

        text = page.text.lower()
        match = re.search(r"(\d\.\d)\s*out of\s*5", text)

        if match:
            score = match.group(1)
            print(f"✅ {business_name} Trustpilot Score: {score}")
            return score
        else:
            print(f"❌ Score not found on page for: {business_name}")
            return "Not found"

    except Exception as e:
        print(f"⚠️ Error fetching Trustpilot for {business_name}: {e}")
        return "Error"

# Get unique business names and cache results
unique_names = df["business_name"].dropna().unique()
score_cache = {}

for name in unique_names:
    score_cache[name] = get_trustpilot_score(name)
    time.sleep(1.5)  # polite delay

# Update DataFrame with scores
df["trustpilot_score"] = df["business_name"].map(score_cache)

# Save over the original CSV file
df.to_csv(csv_path, index=False)
print(f"\n✅ CSV updated with Trustpilot scores and saved to: {csv_path}")
