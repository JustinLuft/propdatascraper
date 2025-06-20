import pandas as pd
from scrapers.scraper_tradeify import scrape_site_tradeify  # Import the function directly

def main():
    try:
        # Run all scrapers
        print("Starting Tradeify scraper...")
        data_a = scrape_site_tradeify()
        
        # Combine data (currently just one scraper)
        all_data = data_a
        
        if not all_data:
            print("No data was scraped. Please check the scraper configuration.")
            return
        
        # Save to CSV
        df = pd.DataFrame(all_data)
        df.to_csv('combined_data.csv', index=False)
        print(f"Saved {len(all_data)} records to combined_data.csv")
        
        # Print summary of scraped data
        print("\nScraped data summary:")
        for i, record in enumerate(all_data, 1):
            print(f"Record {i}: {record.get('plan_name', 'Unknown Plan')} - {record.get('price_raw', 'No price')}")
            
    except ImportError as e:
        print(f"Import error: {e}")
        print("Make sure the scrapers directory exists and contains scraper_tradeify.py")
    except Exception as e:
        print(f"Error in main: {e}")

if __name__ == "__main__":
    main()
