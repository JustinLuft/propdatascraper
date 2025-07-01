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

# Usage example:
# For your CSV, you would call it like:
# score = get_trustpilot_score("https://tradeify.co/plan")
# This would extract "tradeify.co", search for it, and return "4.8"
