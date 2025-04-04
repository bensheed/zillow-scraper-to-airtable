import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from pyairtable import Api
import logging
import time
import random

# --- Configuration ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Load Environment Variables ---
load_dotenv()
# Use AIRTABLE_ACCESS_TOKEN now, as saved by config_app.py
AIRTABLE_ACCESS_TOKEN = os.getenv("AIRTABLE_ACCESS_TOKEN")
AIRTABLE_BASE_ID = os.getenv("AIRTABLE_BASE_ID")
# AIRTABLE_TABLE_NAME = os.getenv("AIRTABLE_TABLE_NAME") # Removed - will be derived from ZIP
ZILLOW_ZIP_CODE = os.getenv("ZILLOW_ZIP_CODE")

# --- Functions ---

def fetch_zillow_data(url):
    """Fetches HTML content from the Zillow search URL."""
    if not url or not url.startswith('http'):
        logging.error("Invalid or missing ZILLOW_SEARCH_URL in .env file.")
        return None

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Connection': 'keep-alive'
    }
    logging.info(f"Attempting to fetch data from: {url}")
    try:
        # Add a small random delay
        time.sleep(random.uniform(2, 5))
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
        logging.info(f"Successfully fetched data (Status Code: {response.status_code}).")
        return response.text
    except requests.exceptions.RequestException as e:
        logging.error(f"Error fetching Zillow data: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logging.error(f"Response status code: {e.response.status_code}")
            # Consider saving or logging e.response.text for debugging anti-scraping measures
            # logging.debug(f"Response content: {e.response.text[:500]}...") # Be careful logging potentially large responses
        return None

def parse_zillow_html(html_content):
    """Parses the Zillow HTML to extract property listings."""
    if not html_content:
        logging.error("No HTML content received for parsing.")
        return []

    soup = BeautifulSoup(html_content, 'html.parser')
    properties = []

    # !!! CRITICAL: These selectors are placeholders and WILL likely need updating !!!
    # Inspect the Zillow search results page source code to find the correct selectors.
    # Look for a container element that holds all the property cards.
    property_cards = soup.find_all('article', class_='list-card') # Example selector, adjust as needed

    if not property_cards:
        logging.warning("Could not find property cards using the specified selectors. The website structure might have changed, or the page didn't load correctly (check for CAPTCHAs or blocks).")
        # You might want to save the HTML content here for inspection:
        # with open("zillow_page_content.html", "w", encoding="utf-8") as f:
        #     f.write(html_content)
        # logging.info("Saved HTML content to zillow_page_content.html for debugging.")
        return []

    logging.info(f"Found {len(property_cards)} potential property cards.")

    for card in property_cards:
        try:
            # --- Extract Data (Adjust Selectors As Needed) ---
            address_tag = card.find('address', class_='list-card-addr')
            price_tag = card.find('div', class_='list-card-price')
            details_tag = card.find('ul', class_='list-card-details') # Container for beds, baths, sqft
            link_tag = card.find('a', class_='list-card-link') # Often the main link for the card

            address = address_tag.text.strip() if address_tag else 'N/A'
            price = price_tag.text.strip() if price_tag else 'N/A'
            url = link_tag['href'] if link_tag and link_tag.has_attr('href') else 'N/A'
            # Ensure the URL is absolute
            if url.startswith('/'):
                url = f"https://www.zillow.com{url}"

            # Extract details (beds, baths, sqft) - this often requires more specific parsing
            beds, baths, sqft = 'N/A', 'N/A', 'N/A'
            if details_tag:
                details_items = details_tag.find_all('li')
                # This logic assumes a specific order or content pattern, adjust as needed
                for item in details_items:
                    text = item.text.lower()
                    if 'bd' in text or 'bed' in text:
                        beds = item.find('span').text.strip() if item.find('span') else item.text.strip()
                    elif 'ba' in text or 'bath' in text:
                        baths = item.find('span').text.strip() if item.find('span') else item.text.strip()
                    elif 'sqft' in text or 'sq ft' in text:
                        sqft = item.find('span').text.strip() if item.find('span') else item.text.strip()

            property_data = {
                # Match these keys to your Airtable column names EXACTLY
                'Address': address,
                'Price': price,
                'Beds': beds,
                'Baths': baths,
                'Sqft': sqft,
                'URL': url
            }
            properties.append(property_data)
            # logging.debug(f"Parsed property: {address}")

        except Exception as e:
            logging.warning(f"Could not parse a property card: {e}. Skipping card.")
            # logging.debug(f"Problematic card HTML snippet: {card.prettify()[:500]}...") # Log snippet for debugging
            continue

    logging.info(f"Successfully parsed {len(properties)} properties.")
    return properties


# Updated function signature: removed table_name parameter
def send_to_airtable(data, access_token, base_id, zip_code):
    """Sends the scraped property data to an Airtable table named after the ZIP code."""
    # Determine table name from ZIP code
    table_name = f"ZIP_{zip_code}"

    # Updated check: removed table_name
    if not all([access_token, base_id, zip_code]):
        logging.error("Missing Airtable credentials (Access Token, Base ID) or ZIP Code.")
        return False
    if not data:
        logging.warning("No data provided to send to Airtable.")
        return False

    # TODO: Implement table existence check and creation using Airtable Metadata API
    # TODO: Implement upsert logic using MLS ID as key field

    try:
        api = Api(access_token)
        # Get table object using the derived name
        table = api.table(base_id, table_name)
        logging.info(f"Attempting to send {len(data)} records to table '{table_name}' in base '{base_id}'.")

        added_count = 0
        for record in data:
             try:
                 # Ensure keys in 'record' match Airtable field names
                 # TODO: Change table.create to table.upsert once MLS ID is added and set as key field
                 table.create(record)
                 added_count += 1
                 logging.debug(f"Added record to Airtable: {record.get('Address', 'N/A')}")
                 time.sleep(0.2) # Airtable API rate limit is typically 5 requests per second
             except Exception as e:
                 logging.error(f"Failed to add record {record.get('Address', 'N/A')} to Airtable table '{table_name}': {e}")
                 # Consider logging the specific record data that failed
                 # logging.debug(f"Failed record data: {record}")

        logging.info(f"Successfully added {added_count}/{len(data)} records to Airtable table '{table_name}'.")
        return added_count > 0

    except Exception as e:
        # This might catch errors if the table doesn't exist yet
        logging.error(f"Error connecting to or writing to Airtable table '{table_name}': {e}")
        logging.error(f"Ensure table '{table_name}' exists in base '{base_id}' with correct columns (Address, Price, Beds, Baths, Sqft, URL).")
        return False

# --- Main Execution ---
if __name__ == "__main__":
    logging.info("--- Starting Zillow Scraper ---")

    # 1. Check Credentials
    # Updated check: Removed AIRTABLE_TABLE_NAME
    if not all([AIRTABLE_ACCESS_TOKEN, AIRTABLE_BASE_ID, ZILLOW_ZIP_CODE]):
        logging.error("One or more required environment variables (Airtable Access Token, Base ID, Zillow ZIP Code) are missing in .env. Please run config_app.py first. Exiting.")
        exit(1)
    # Updated placeholder/format check: Removed AIRTABLE_TABLE_NAME
    if "YOUR_" in AIRTABLE_ACCESS_TOKEN or not AIRTABLE_ACCESS_TOKEN.startswith("pat") \
       or "YOUR_" in AIRTABLE_BASE_ID \
       or not (ZILLOW_ZIP_CODE and ZILLOW_ZIP_CODE.isdigit() and len(ZILLOW_ZIP_CODE) == 5):
         logging.warning("Placeholder values or invalid token/Base ID/ZIP code format detected in .env file. Please run config_app.py to set actual credentials and ZIP Code.")
         exit(1) # Exit if placeholders/invalid format found

    # 2. Construct Zillow URL and Fetch Data
    # Construct the URL from the ZIP code
    zillow_url_to_scrape = f"https://www.zillow.com/homes/for_sale/{ZILLOW_ZIP_CODE}_rb/"
    logging.info(f"Constructed Zillow URL: {zillow_url_to_scrape}")

    html = fetch_zillow_data(zillow_url_to_scrape)

    if html:
        # 3. Parse Data
        properties_data = parse_zillow_html(html)

        if properties_data:
            # 4. Send to Airtable
            # Updated to pass ZILLOW_ZIP_CODE instead of table name
            success = send_to_airtable(properties_data, AIRTABLE_ACCESS_TOKEN, AIRTABLE_BASE_ID, ZILLOW_ZIP_CODE)
            if success:
                logging.info("--- Scraper finished successfully ---")
            else:
                logging.error("--- Scraper finished with errors during Airtable upload ---")
        else:
            logging.warning("--- No properties parsed, nothing to send to Airtable ---")
    else:
        logging.error("--- Failed to fetch Zillow page, scraper aborted ---")

    logging.info("--- Zillow Scraper finished ---")
