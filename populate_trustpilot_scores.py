import urllib.parse
import re
from difflib import SequenceMatcher

def get_trustpilot_score(business_name: str) -> str:
    try:
        print(f"🔍 Searching Trustpilot for: {business_name}")
        query = urllib.parse.quote(business_name)
        search_url = f"https://www.trustpilot.com/search?query={query}"
        
        # Step 1: Scrape the search results page
        search_page = app.scrape_url(
            url=search_url,
            formats=["html"],
            only_main_content=False,
            timeout=90000
        )
        
        # Step 2: Try to extract rating directly from search results first
        html_content = search_page.html
        
        # Look for the rating pattern in search results (more reliable)
        # Pattern matches: "4.8 • 635 reviews" or similar
        rating_patterns = [
            r'(\d\.\d)\s*•\s*\d+\s*reviews?',  # "4.8 • 635 reviews"
            r'(\d\.\d)\s*out\s*of\s*5',        # "4.8 out of 5"
            r'rating["\s]*:\s*["\s]*(\d\.\d)',  # JSON-like "rating": "4.8"
            r'(\d\.\d)\s*stars?',               # "4.8 stars"
        ]
        
        # Try each pattern
        for pattern in rating_patterns:
            matches = re.findall(pattern, html_content.lower())
            if matches:
                # If we found ratings, try to match with business name
                business_sections = re.split(r'<div[^>]*class[^>]*search-result', html_content, flags=re.IGNORECASE)
                
                for i, section in enumerate(business_sections[1:], 1):  # Skip first split
                    # Check if this section contains our business name
                    if is_business_match(business_name, section):
                        # Look for rating in this specific section
                        for pattern in rating_patterns:
                            section_matches = re.findall(pattern, section.lower())
                            if section_matches:
                                score = section_matches[0]
                                print(f"✅ {business_name} score from search results: {score}")
                                return score
                
                # If no specific match found, but we have ratings, take first one
                if matches:
                    score = matches[0]
                    print(f"⚠️ {business_name} score (best guess from search): {score}")
                    return score
        
        # Step 3: Fallback to profile page method (improved)
        print("🔄 Trying profile page method...")
        
        # Extract business profile links with better matching
        profile_links = re.findall(r'https://www\.trustpilot\.com/review/[a-zA-Z0-9\.-]+', html_content)
        
        if not profile_links:
            print(f"❌ No business profile found for: {business_name}")
            return "Not found"
        
        # Try to find the best matching profile
        best_link = find_best_matching_link(business_name, profile_links, html_content)
        print(f"🔗 Found profile: {best_link}")
        
        # Step 4: Scrape the business profile page
        profile_page = app.scrape_url(
            url=best_link,
            formats=["html"],
            only_main_content=False,
            timeout=90000
        )
        
        # Step 5: Extract the rating with better patterns
        profile_html = profile_page.html.lower()
        
        # More specific patterns for profile pages
        profile_patterns = [
            r'trustscore["\s]*[:\s]*["\s]*(\d\.\d)',     # TrustScore specific
            r'(\d\.\d)\s*out\s*of\s*5\s*based\s*on',    # "4.8 out of 5 based on"
            r'rating["\s]*:\s*["\s]*(\d\.\d)',          # JSON rating
            r'(\d\.\d)\s*out\s*of\s*5',                 # Generic "out of 5"
        ]
        
        for pattern in profile_patterns:
            match = re.search(pattern, profile_html)
            if match:
                score = match.group(1)
                print(f"✅ {business_name} score from profile: {score}")
                return score
        
        print(f"❌ Score not found on business page for {business_name}")
        return "Not found"
        
    except Exception as e:
        print(f"⚠️ Error for {business_name}: {e}")
        return "Error"

def is_business_match(business_name: str, html_section: str) -> bool:
    """Check if HTML section contains the business we're looking for"""
    business_lower = business_name.lower()
    section_lower = html_section.lower()
    
    # Remove HTML tags for cleaner text matching
    clean_section = re.sub(r'<[^>]+>', ' ', section_lower)
    
    # Simple word matching
    business_words = business_lower.split()
    matches = sum(1 for word in business_words if word in clean_section)
    
    # Consider it a match if most words are found
    return matches >= len(business_words) * 0.6

def find_best_matching_link(business_name: str, links: list, html_content: str) -> str:
    """Find the profile link that best matches the business name"""
    if len(links) == 1:
        return links[0]
    
    business_lower = business_name.lower()
    best_link = links[0]
    best_score = 0
    
    for link in links:
        # Extract domain from link
        domain_match = re.search(r'/review/([^/?]+)', link)
        if domain_match:
            domain = domain_match.group(1)
            # Calculate similarity between business name and domain
            score = SequenceMatcher(None, business_lower, domain.lower()).ratio()
            
            # Also check if the link appears near the business name in HTML
            link_context = get_link_context(link, html_content)
            if business_lower in link_context.lower():
                score += 0.3  # Boost score if business name appears near link
            
            if score > best_score:
                best_score = score
                best_link = link
    
    return best_link

def get_link_context(link: str, html_content: str, context_size: int = 500) -> str:
    """Get text context around a link in HTML"""
    link_pos = html_content.find(link)
    if link_pos == -1:
        return ""
    
    start = max(0, link_pos - context_size)
    end = min(len(html_content), link_pos + len(link) + context_size)
    
    return html_content[start:end]
