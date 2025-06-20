import pandas as pd
from scrapers.scraper_tradeify import scrape_site_tradeify  # Import the function directly
from scrapers.apex_trader_funding_scraper import ApexTraderFundingScraper  # Import the Apex scraper class

def scrape_apex_trader():
    """Wrapper function to scrape Apex Trader Funding and return data in consistent format"""
    try:
        scraper = ApexTraderFundingScraper()
        plans = scraper.scrape_main_page()
        scraper.scrape_additional_pages()  # Get additional data if available
        
        # Convert ApexTraderFunding data to consistent format
        apex_data = []
        for plan in scraper.plans:
            apex_data.append({
                'business_name': plan.business_name,
                'plan_name': f"{plan.account_size} Account",
                'account_size': plan.account_size,
                'price_raw': plan.sale_price,
                'funded_price': plan.funded_full_price,
                'discount_code': plan.discount_code,
                'trial_type': plan.trial_type,
                'trustpilot_score': plan.trustpilot_score,
                'profit_goal': plan.profit_goal,
                'source': 'Apex Trader Funding'
            })
        
        print(f"Apex Trader Funding: Scraped {len(apex_data)} plans")
        return apex_data
        
    except Exception as e:
        print(f"Error scraping Apex Trader Funding: {e}")
        return []

def main():
    try:
        all_data = []
        
        # Run Tradeify scraper
        print("Starting Tradeify scraper...")
        data_tradeify = scrape_site_tradeify()
        if data_tradeify:
            # Add source identifier to Tradeify data
            for record in data_tradeify:
                record['source'] = 'Tradeify'
            all_data.extend(data_tradeify)
            print(f"Tradeify: Successfully scraped {len(data_tradeify)} records")
        else:
            print("Tradeify: No data scraped")
        
        # Run Apex Trader Funding scraper
        print("\nStarting Apex Trader Funding scraper...")
        data_apex = scrape_apex_trader()
        if data_apex:
            all_data.extend(data_apex)
            print(f"Apex Trader Funding: Successfully scraped {len(data_apex)} records")
        else:
            print("Apex Trader Funding: No data scraped")
        
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
        print("  - scrapers/apex_trader_funding_scraper.py")
    except Exception as e:
        print(f"Error in main: {e}")

if __name__ == "__main__":
    main()
