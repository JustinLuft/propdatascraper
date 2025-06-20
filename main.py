import pandas as pd
from scrapers.scraper_tradeify import TradeifyScraper

def main():
    # Run all scrapers
    data_a = scrape_site_tradeify()
    
    # Combine data
    all_data = data_a + data_b + data_c
    
    # Save to CSV
    df = pd.DataFrame(all_data)
    df.to_csv('combined_data.csv', index=False)
    print(f"Saved {len(all_data)} records to combined_data.csv")

if __name__ == "__main__":
    main()
