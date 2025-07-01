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

        # Step 2: Extract the first business profile link
        links = re.findall(r'https://www\.trustpilot\.com/review/[a-zA-Z0-9\.-]+', search_page.html)
        if not links:
            print(f"❌ No business profile found for: {business_name}")
            return "Not found"

        profile_url = links[0]
        print(f"🔗 Found profile: {profile_url}")

        # Step 3: Scrape the business profile page
        profile_page = app.scrape_url(
            url=profile_url,
            formats=["html"],
            only_main_content=False,
            timeout=90000
        )

        # Step 4: Extract the rating
        text = profile_page.html.lower()
        match = re.search(r"(\d\.\d)\s*out of\s*5", text)

        if match:
            score = match.group(1)
            print(f"✅ {business_name} score: {score}")
            return score
        else:
            print(f"❌ Score not found on business page for {business_name}")
            return "Not found"

    except Exception as e:
        print(f"⚠️ Error for {business_name}: {e}")
        return "Error"
