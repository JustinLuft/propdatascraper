import urllib.parse
import re
from urllib.parse import urlparse

def get_trustpilot_score(source_url: str, app, max_retries: int = 3) -> str:
    for attempt in range(max_retries):
        try:
            # Extract domain from source URL
            parsed_url = urlparse(source_url)
            domain = parsed_url.netloc
            # Remove 'www.' if present
            if domain.startswith('www.'):
                domain = domain[4:]
            
            print(f"🔍 Searching Trustpilot for domain: {domain} (attempt {attempt + 1}/{max_retries})")
            
            # Search Trustpilot using the domain
            query = urllib.parse.quote(domain)
            search_url = f"https://www.trustpilot.com/search?query={query}"
            
            # Add a small delay to avoid rate limiting
            import time
            if attempt > 0:  # Only delay on retries
                time.sleep(5)  # 5 second delay on retries
            else:
                time.sleep(2)  # 2 second delay on first attempt
            
            # Step 1: Scrape the search results page
            search_page = app.scrape_url(
                url=search_url,
                formats=["html"],
                only_main_content=False,
                timeout=90000
            )
        
        html_content = search_page.html
        
        # Debug: Print some of the HTML to see what we're working with
        print(f"📝 HTML snippet: {html_content[:500]}...")
        
        # FIRST: Try to find ratings specifically for our domain
        # Look for the domain in href or company name context
        domain_specific_patterns = [
            # Pattern that looks for our domain in href followed by rating
            rf'href="[^"]*{re.escape(domain)}[^"]*"[^>]*>.*?(\d\.\d)\s*[•·]\s*[\d,]+\s*reviews?',
            # Pattern that looks for domain name followed by rating nearby
            rf'{re.escape(domain)}.*?(\d\.\d)\s*[•·]\s*[\d,]+\s*reviews?',
            # Pattern for business unit card containing our domain
            rf'business-unit-card[^>]*>[^<]*{re.escape(domain)}[^<]*<.*?(\d\.\d)\s*[•·]\s*[\d,]+\s*reviews?'
        ]
        
        print(f"🎯 Looking for domain-specific ratings for: {domain}")
        for i, pattern in enumerate(domain_specific_patterns):
            matches = re.findall(pattern, html_content, re.IGNORECASE | re.DOTALL)
            if matches:
                score = matches[0] if isinstance(matches[0], str) else matches[0][0]
                print(f"✅ {domain} score found with domain-specific pattern {i+1}: {score}")
                return score
        
        # FALLBACK: If domain-specific search fails, use generic patterns
        print(f"🔄 Domain-specific search failed, trying generic patterns...")
        
        # Enhanced rating patterns to catch more variations
        rating_patterns = [
            # Main pattern with bullet and comma support: "4.8 • 34,148 reviews"
            r'(\d\.\d)\s*•\s*[\d,]+\s*reviews?',
            # Pattern with different separators and comma support
            r'(\d\.\d)\s*[-–—]\s*[\d,]+\s*reviews?',
            r'(\d\.\d)\s*\|\s*[\d,]+\s*reviews?',
            # More flexible pattern with comma support
            r'(\d\.\d)\s*[•\-–—\|]?\s*[\d,]+\s*reviews?',
            # Pattern specifically for the format: "4.8 • 635 reviews" or "2.5 • 34,148 reviews"
            r'(\d\.\d)\s*[•·]\s*[\d,]+\s*reviews?',
            # Backup patterns without comma requirement
            r'(\d\.\d)\s*•\s*\d+\s*reviews?',
            r'(\d\.\d)\s*[•·]\s*\d+\s*reviews?'
        ]
        
        for i, pattern in enumerate(rating_patterns):
            matches = re.findall(pattern, html_content, re.IGNORECASE | re.DOTALL)
            if matches:
                # Extract just the rating (first capture group)
                if isinstance(matches[0], tuple):
                    score = matches[0][0]  # First element of tuple
                else:
                    score = matches[0]
                print(f"✅ {domain} score found with pattern {i+1}: {score}")
                return score
        
        # Additional fallback patterns
        fallback_patterns = [
            r'(\d\.\d)\s*out\s*of\s*5',
            r'rating["\s]*:\s*["\s]*(\d\.\d)',
            r'(\d\.\d)\s*stars?',
            # Look for JSON-like data
            r'"rating":\s*"?(\d\.\d)"?',
            r'"score":\s*"?(\d\.\d)"?',
            # Look for microdata
            r'ratingValue["\s]*:\s*["\s]*(\d\.\d)',
            # Very broad search for any decimal rating
            r'(?:rating|score|stars?).*?(\d\.\d)',
        ]
        
        print(f"🔄 Trying fallback patterns...")
        for i, pattern in enumerate(fallback_patterns):
            matches = re.findall(pattern, html_content, re.IGNORECASE)
            if matches:
                score = matches[0]
                print(f"✅ {domain} score (fallback {i+1}): {score}")
                return score
        
        print(f"❌ No rating found for: {domain}")
        
        # Debug: Let's see if "reviews" appears at all
        if "reviews" in html_content.lower():
            print(f"🔍 Found 'reviews' in content, but couldn't match rating pattern")
            # Try to find any number followed by "reviews"
            review_matches = re.findall(r'(\d+)\s*reviews?', html_content, re.IGNORECASE)
            if review_matches:
                print(f"📊 Found review counts: {review_matches[:3]}")  # Show first 3
        
        return "Not found"
        
    except Exception as e:
        print(f"⚠️ Error for {source_url} (attempt {attempt + 1}): {e}")
        if attempt == max_retries - 1:  # Last attempt
            return "Error"
        else:
            print(f"🔄 Retrying in 5 seconds...")
            time.sleep(5)
    
    return "Error"  # Fallback if all retries failed

# Main execution code remains the same
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
