import pandas as pd
from scrapers.scraper_tradeify import TradeifyScraper  # Import the class
from scrapers.scraper_apex import ApexTraderFundingScraper  # Import the class
from scrapers.scraper_myfundedfuture import MyFundedFuturesScraper  # Import the class

def main():
    try:
        all_data = []
        
        # Run Tradeify scraper
        print("Starting Tradeify scraper...")
        try:
            tradeify_scraper = TradeifyScraper()  # Create instance of the class
            tradeify_plans = tradeify_scraper.scrape_all()  # Call the scrape method
            data_tradeify = tradeify_scraper.get_standardized_data()  # Get standardized data
            
            if data_tradeify:
                # Add source identifier to Tradeify data if not already present
                for record in data_tradeify:
                    if 'source' not in record:
                        record['source'] = 'Tradeify'
                all_data.extend(data_tradeify)
                print(f"Tradeify: Successfully scraped {len(data_tradeify)} records")
            else:
                print("Tradeify: No data scraped")
        except Exception as e:
            print(f"Error with Tradeify scraper: {e}")
        
        # Run Apex Trader Funding scraper
        print("\nStarting Apex Trader Funding scraper...")
        try:
            apex_scraper = ApexTraderFundingScraper()  # Create instance of the class
            # Use the correct method name - scrape_main_page() instead of scrape_all()
            apex_plans = apex_scraper.scrape_main_page()  # Call the correct scrape method
            
            # Also try to scrape additional pages for more comprehensive data
            if apex_plans:
                apex_scraper.scrape_additional_pages()
            
            data_apex = apex_scraper.get_standardized_data()  # Get standardized data
            
            if data_apex:
                all_data.extend(data_apex)
                print(f"Apex Trader Funding: Successfully scraped {len(data_apex)} records")
            else:
                print("Apex Trader Funding: No data scraped")
        except Exception as e:
            print(f"Error with Apex scraper: {e}")
        
        # Run My Funded Futures scraper
        print("\nStarting My Funded Futures scraper...")
        try:
            mff_scraper = MyFundedFuturesScraper()  # Create instance of the class
            mff_plans = mff_scraper.scrape_main_page()  # Call the scrape method
            
            # Also try to scrape additional pages for more comprehensive data
            if mff_plans:
                mff_scraper.scrape_additional_pages()
            
            data_mff = mff_scraper.get_standardized_data()  # Get standardized data
            
            if data_mff:
                all_data.extend(data_mff)
                print(f"My Funded Futures: Successfully scraped {len(data_mff)} records")
            else:
                print("My Funded Futures: No data scraped")
        except Exception as e:
            print(f"Error with My Funded Futures scraper: {e}")
        
        if not all_data:
            print("No data was scraped from any source. Please check the scraper configurations.")
            return
        
        # Save to CSV
        df = pd.DataFrame(all_data)
        df.to_csv('combined_data.csv', index=False)
        print(f"\nSaved {len(all_data)} total records to combined_data.csv")
        
        # Print summary of scraped data by source
        print("\nScraped data summary:")
        sources = {}
        for record in all_data:
            source = record.get('source', 'Unknown')
            if source not in sources:
                sources[source] = []
            sources[source].append(record)
        
        for source, records in sources.items():
            print(f"\n{source} ({len(records)} records):")
            for i, record in enumerate(records, 1):
                plan_name = record.get('plan_name', record.get('account_size', 'Unknown Plan'))
                price = record.get('price_raw', 'No price')
                print(f"  Record {i}: {plan_name} - {price}")
                
    except ImportError as e:
        print(f"Import error: {e}")
        print("Make sure the scrapers directory exists and contains the required scraper files")
        print("Required files:")
        print("  - scrapers/scraper_tradeify.py") 
        print("  - scrapers/scraper_apex.py")
        print("  - scrapers/scraper_myfundedfuture.py")
    except Exception as e:
        print(f"Error in main: {e}")

if __name__ == "__main__":
    main()
