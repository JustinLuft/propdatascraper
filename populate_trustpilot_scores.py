import pandas as pd
import time
import re
import os
from firecrawl import FirecrawlApp

# Initialize Firecrawl with API key from environment variable
api_key = os.getenv("FIRECRAWL_API_KEY")
app = FirecrawlApp(api_key=api_key)

# Load CSV
csv_path = "plans_output.csv"
df = pd.read_csv(csv_path)

# Function to get Trustpilot score
def get_trustpilot_score(business_name: str) -> str:
    try:
        # Google-style query
        query = f"site:trustpilot.com {business_name}"
        search = app.search(query=query, num_results=1)
        trustpilot_url = search.results[0].url

        # Scrape Trustpilot page
        page = app.scrape_url(
            url=trustpilot_url,
            formats=["text"],
            only_main_content=False,
            timeout=60000
        )

        # Parse out score
        text = page.text.lower()
        match = re.search(r"(\d\.\d)\s*out of\s*5", text)
        if match:
            print(f"✔ {business_name}: {match.group(1)}")
            return match.group(1)
        else:
            print(f"✘ {business_name}: Not found")
            return "Not found"

    except Exception as e:
        print(f"⚠️ Error for {business_name}: {e}")
        return "Error"

# Get unique business names
unique_names = df["business_name"].dropna().unique()
score_cache = {}

# Fetch scores (cache avoids re-querying duplicates)
for name in unique_names:
    score_cache[name] = get_trustpilot_score(name)
    time.sleep(1.5)  # Rate limit for safety

# Apply scores back into DataFrame
df["trustpilot_score"] = df["business_name"].map(score_cache)

# Save updated CSV (overwrite or new file)
updated_csv_path = "plans_output_with_scores.csv"
df.to_csv(updated_csv_path, index=False)

print(f"\n✅ Updated CSV saved as {updated_csv_path}")
