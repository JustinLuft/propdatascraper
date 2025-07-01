import urllib.parse
import re
from urllib.parse import urlparse

def get_trustpilot_score(source_url: str) -> str:
    try:
        # Extract domain from source URL
        parsed_url = urlparse(source_url)
        domain = parsed_url.netloc
        # Remove 'www.' if present
        if domain.startswith('www.'):
            domain = domain[4:]
        
        print(f"🔍 Searching Trustpilot for domain: {domain}")
        
        # Search Trustpilot using the domain
        query = urllib.parse.quote(domain)
        search_url = f"https://www.trustpilot.com/search?query={query}"
        
        # Step 1: Scrape the search results page
        search_page = app.scrape_url(
            url=search_url,
            formats=["html"],
            only_main_content=False,
            timeout=90000
        )
        
        html_content = search_page.html
        
        # Step 2: Look for the first rating in search results
        # Pattern matches: "4.8 • 635 reviews" format from your screenshot
        rating_pattern = r'(\d\.\d)\s*•\s*\d+\s*reviews?'
        matches = re.findall(rating_pattern, html_content, re.IGNORECASE)
        
        if matches:
            # Return the first (top) result's rating
            score = matches[0]
            print(f"✅ {domain} score: {score}")
            return score
        
        # Fallback: Look for other rating patterns in search results
        fallback_patterns = [
            r'(\d\.\d)\s*out\s*of\s*5',
            r'rating["\s]*:\s*["\s]*(\d\.\d)',
            r'(\d\.\d)\s*stars?'
        ]
        
        for pattern in fallback_patterns:
            matches = re.findall(pattern, html_content.lower())
            if matches:
                score = matches[0]
                print(f"✅ {domain} score (fallback): {score}")
                return score
        
        print(f"❌ No rating found for: {domain}")
        return "Not found"
        
    except Exception as e:
        print(f"⚠️ Error for {source_url}: {e}")
        return "Error"

# Main execution code
import pandas as pd
import os

def populate_trustpilot_scores():
    # Find CSV file (adjust filename as needed)
    csv_files = [f for f in os.listdir('.') if f.endswith('.csv')]
    if not csv_files:
        print("❌ No CSV file found!")
        return
    
    csv_file = csv_files[0]  # Take first CSV file found
    print(f"📄 Processing file: {csv_file}")
    
    # Read CSV
    df = pd.read_csv(csv_file)
    print(f"📊 Found {len(df)} rows")
    
    # Check if required columns exist
    if 'source_url' not in df.columns:
        print("❌ No 'source_url' column found!")
        return
    
    # Add trustpilot_score column if it doesn't exist
    if 'trustpilot_score' not in df.columns:
        df['trustpilot_score'] = ''
    
    # Process each row
    updated_count = 0
    for index, row in df.iterrows():
        source_url = row['source_url']
        current_score = row.get('trustpilot_score', '')
        
        # Skip if already has a score (unless it's empty, "Not found", or "Error")
        if current_score and current_score not in ['', 'Not found', 'Error']:
            print(f"⏭️ Skipping {source_url} (already has score: {current_score})")
            continue
        
        print(f"\n🔄 Processing row {index + 1}/{len(df)}: {source_url}")
        
        # Get Trustpilot score
        score = get_trustpilot_score(source_url)
        
        # Update the dataframe
        df.at[index, 'trustpilot_score'] = score
        updated_count += 1
        
        print(f"📝 Updated row {index + 1} with score: {score}")
    
    # Save the updated CSV
    df.to_csv(csv_file, index=False)
    print(f"\n✅ Completed! Updated {updated_count} rows in {csv_file}")

if __name__ == "__main__":
    # You need to initialize the 'app' object here
    # This should be your Firecrawl app instance
    # Example: app = FirecrawlApp(api_key="your_api_key")
    
    print("🚀 Starting Trustpilot score population...")
    populate_trustpilot_scores()
