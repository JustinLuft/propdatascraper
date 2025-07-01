import urllib.parse
import re
from urllib.parse import urlparse

def get_trustpilot_score(source_url: str, app) -> str:
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

def populate_trustpilot_scores(app):
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
    
    # Check if required columns exist and find the URL column
    print(f"📋 Available columns: {list(df.columns)}")
    
    url_column = None
    possible_url_columns = ['source_url', 'source url', 'url', 'website', 'link']
    
    for col in possible_url_columns:
        if col in df.columns:
            url_column = col
            break
    
    if not url_column:
        print(f"❌ No URL column found! Available columns: {list(df.columns)}")
        print("Looking for one of: source_url, source url, url, website, link")
        return
    
    print(f"✅ Using URL column: '{url_column}'")
    
    # Add trustpilot_score column if it doesn't exist
    if 'trustpilot_score' not in df.columns:
        df['trustpilot_score'] = ''
    
    # Process each row - track domains to avoid duplicate API calls
    updated_count = 0
    domain_scores = {}  # Cache scores by domain
    
    for index, row in df.iterrows():
        source_url = row[url_column]  # Use the detected column name
        
        # Extract domain to check if we've already processed it
        try:
            parsed_url = urlparse(source_url)
            domain = parsed_url.netloc
            if domain.startswith('www.'):
                domain = domain[4:]
        except:
            domain = source_url
        
        print(f"\n🔄 Processing row {index + 1}/{len(df)}: {source_url}")
        
        # Check if we already have the score for this domain
        if domain in domain_scores:
            score = domain_scores[domain]
            print(f"♻️ Using cached score for {domain}: {score}")
        else:
            # Get Trustpilot score (first time for this domain)
            score = get_trustpilot_score(source_url, app)
            domain_scores[domain] = score  # Cache the result
        
        # Always update the dataframe (even if score was cached)
        df.at[index, 'trustpilot_score'] = score
        updated_count += 1
        
        print(f"📝 Updated row {index + 1} with score: {score}")
    
    # Save the updated CSV
    df.to_csv(csv_file, index=False)
    print(f"\n✅ Completed! Updated {updated_count} rows in {csv_file}")

if __name__ == "__main__":
    # Initialize the Firecrawl app
    from firecrawl import FirecrawlApp
    import os
    
    app = FirecrawlApp(api_key=os.getenv("FIRECRAWL_API_KEY"))
    
    print("🚀 Starting Trustpilot score population...")
    populate_trustpilot_scores(app)
