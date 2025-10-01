import urllib.parse
import re
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
import time
import pandas as pd
import os

def get_trustpilot_score(source_url: str, max_retries: int = 3) -> str:
    for attempt in range(max_retries):
        try:
            # Extract domain from source URL
            parsed_url = urlparse(source_url)
            domain = parsed_url.netloc
            # Remove 'www.' if present
            if domain.startswith('www.'):
                domain = domain[4:]
            
            print(f"🔍 Searching Trustpilot for domain: {domain} (attempt {attempt + 1}/{max_retries})")
            
            # Try direct Trustpilot review page first
            direct_url = f"https://www.trustpilot.com/review/{domain}"
            
            # Set up headers to avoid being blocked
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            }
            
            # Add delay to avoid rate limiting
            if attempt > 0:
                time.sleep(5)
            else:
                time.sleep(2)
            
            # First try direct URL
            print(f"🎯 Trying direct URL: {direct_url}")
            response = requests.get(direct_url, headers=headers, timeout=30)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Look for rating in various places
                rating_selectors = [
                    # Common Trustpilot rating selectors
                    '[data-rating]',
                    '.star-rating',
                    '[class*="star-rating"]',
                    '[class*="rating"]',
                    '.trustScore',
                    '[data-testid*="rating"]',
                    # Text-based patterns
                    'span:contains("out of")',
                    'div:contains("out of")',
                ]
                
                # Try to find rating using CSS selectors
                for selector in rating_selectors:
                    elements = soup.select(selector)
                    for element in elements:
                        # Check data attributes
                        if element.get('data-rating'):
                            score = element.get('data-rating')
                            print(f"✅ Found rating via data-rating: {score}")
                            return score
                        
                        # Check text content
                        text = element.get_text(strip=True)
                        rating_match = re.search(r'(\d\.\d)', text)
                        if rating_match:
                            score = rating_match.group(1)
                            print(f"✅ Found rating in text: {score}")
                            return score
                
                # Search the entire page content for rating patterns
                page_text = soup.get_text()
                
                # Enhanced rating patterns
                rating_patterns = [
                    r'(\d\.\d)\s*out\s*of\s*5',
                    r'(\d\.\d)\s*[•·]\s*[\d,]+\s*reviews?',
                    r'(\d\.\d)\s*[-–—]\s*[\d,]+\s*reviews?',
                    r'TrustScore[^\d]*(\d\.\d)',
                    r'Rating[^\d]*(\d\.\d)',
                    r'(\d\.\d)\s*stars?',
                    r'score[^\d]*(\d\.\d)',
                ]
                
                for pattern in rating_patterns:
                    matches = re.findall(pattern, page_text, re.IGNORECASE)
                    if matches:
                        score = matches[0]
                        print(f"✅ Found rating with pattern: {score}")
                        return score
                
                print(f"🔍 Direct URL found page but no rating extracted")
            
            # If direct URL fails, try search
            print(f"🔄 Trying search approach...")
            query = urllib.parse.quote(domain)
            search_url = f"https://www.trustpilot.com/search?query={query}"
            
            response = requests.get(search_url, headers=headers, timeout=30)
            
            if response.status_code != 200:
                print(f"❌ HTTP {response.status_code} for search URL")
                continue
            
            soup = BeautifulSoup(response.content, 'html.parser')
            page_text = soup.get_text()
            
            print(f"📝 Search page loaded, looking for ratings...")
            
            # Search page patterns - look for ratings near the domain name
            search_patterns = [
                # Look for domain followed by rating
                rf'{re.escape(domain)}.*?(\d\.\d)\s*[•·]\s*[\d,]+\s*reviews?',
                rf'{re.escape(domain)}.*?(\d\.\d)\s*out\s*of\s*5',
                # General rating patterns
                r'(\d\.\d)\s*[•·]\s*[\d,]+\s*reviews?',
                r'(\d\.\d)\s*out\s*of\s*5',
                r'(\d\.\d)\s*[-–—]\s*[\d,]+\s*reviews?',
            ]
            
            for i, pattern in enumerate(search_patterns):
                matches = re.findall(pattern, page_text, re.IGNORECASE | re.DOTALL)
                if matches:
                    score = matches[0] if isinstance(matches[0], str) else matches[0]
                    print(f"✅ Found rating via search pattern {i+1}: {score}")
                    return score
            
            # Look for any links to review pages and extract from those
            review_links = soup.find_all('a', href=re.compile(r'/review/'))
            for link in review_links[:3]:  # Check first 3 links
                href = link.get('href')
                if domain.lower() in href.lower():
                    print(f"🔗 Found specific review link: {href}")
                    # Extract rating from the link text or nearby elements
                    link_text = link.get_text()
                    rating_match = re.search(r'(\d\.\d)', link_text)
                    if rating_match:
                        score = rating_match.group(1)
                        print(f"✅ Found rating in link text: {score}")
                        return score
            
            print(f"❌ No rating found for: {domain}")
            
        except requests.RequestException as e:
            print(f"⚠️ Request error for {source_url} (attempt {attempt + 1}): {e}")
        except Exception as e:
            print(f"⚠️ Error for {source_url} (attempt {attempt + 1}): {e}")
        
        if attempt < max_retries - 1:
            print(f"🔄 Retrying in 5 seconds...")
            time.sleep(5)
    
    return "Not found"

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
        
        # Skip if URL is empty or NaN
        if pd.isna(source_url) or not source_url:
            print(f"⏭️ Skipping row {index + 1}: empty URL")
            continue
        
        # Extract domain to check if we've already processed it
        try:
            parsed_url = urlparse(str(source_url))
            domain = parsed_url.netloc
            if domain.startswith('www.'):
                domain = domain[4:]
        except:
            domain = str(source_url)
        
        print(f"\n🔄 Processing row {index + 1}/{len(df)}: {source_url}")
        
        # Check if we already have the score for this domain
        if domain in domain_scores:
            score = domain_scores[domain]
            print(f"♻️ Using cached score for {domain}: {score}")
        else:
            # Get Trustpilot score (first time for this domain)
            score = get_trustpilot_score(source_url)
            domain_scores[domain] = score  # Cache the result
        
        # Always update the dataframe (even if score was cached)
        df.at[index, 'trustpilot_score'] = score
        updated_count += 1
        
        print(f"📝 Updated row {index + 1} with score: {score}")
    
    # Save the updated CSV
    df.to_csv(csv_file, index=False)
    print(f"\n✅ Completed! Updated {updated_count} rows in {csv_file}")

if __name__ == "__main__":
    print("🚀 Starting Trustpilot score population...")
    print("📦 Required packages: requests, beautifulsoup4, pandas")
    print("   Install with: pip install requests beautifulsoup4 pandas")
    print()
    
    try:
        populate_trustpilot_scores()
    except ImportError as e:
        print(f"❌ Missing required package: {e}")
        print("Please install required packages with:")
        print("pip install requests beautifulsoup4 pandas")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
