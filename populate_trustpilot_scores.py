import pandas as pd
import time
import re
import os
import urllib.parse
from firecrawl import FirecrawlApp

# Initialize Firecrawl with API key
api_key = os.getenv("FIRECRAWL_API_KEY")
app = FirecrawlApp(api_key=api_key)

# Load existing CSV
csv_path = "plans_output.csv"
df = pd.read_csv(csv_path)

# Function to search Trustpilot and extract score
def get_trustpilot_score(business_name: str) -> str:
    try:
        print(f"🔍 Searching Trustpilot for: {business_name}")
        encoded_name = urllib.parse.quote(business_name)
        search_url = f"https://www.trustpilot.com/search?query={encoded_name}"

        # Firecrawl scrape
        page = app.scrape_url(
            url=search_url,
            formats=["html"],  # ✅ use a valid format
            only_main_content=False,
            timeout=90000
        )

        # Parse the score
        text = page.html.lower()  # ✅ use the correct field
        match = re.search(r"(\d\.\d)\s*out of\s*5", text)

        if match:
            score = match.group(1)
            print(f"✅ Found score for {business_name}: {score}")
            return score
        else:
            print(f"❌ Score not found on page for {business_name}")
            return "Not found"

    except Exception as e:
        print(f"⚠️ Error for {business_name}: {e}")
        return "Error"


# Get unique business names and fetch scores
unique_names = df["business_name"].dropna().unique()
score_cache = {}

for name in unique_names:
    score_cache[name] = get_trustpilot_score(name)
    time.sleep(1.5)  # Delay to be polite

# Update DataFrame with scores
df["trustpilot_score"] = df["business_name"].map(score_cache)

# Save updated CSV (overwrite)
df.to_csv(csv_path, index=False)
print(f"\n✅ CSV updated and saved to: {csv_path}")
