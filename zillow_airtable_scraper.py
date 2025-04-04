import os
import requests # Already present, but good to confirm
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from pyairtable import Api
import logging
import time
import random
from datetime import datetime # For Last Seen timestamp

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

# Import Playwright
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

def fetch_zillow_data(url):
    """Fetches HTML content from the Zillow search URL using Playwright."""
    if not url or not url.startswith('http'):
        logging.error("Invalid Zillow URL provided.")
        return None

    logging.info(f"Attempting to fetch data from: {url} using Playwright")
    html_content = None
    with sync_playwright() as p:
        # Try launching Chromium - other browsers like firefox or webkit can also be used
        try:
            browser = p.chromium.launch(headless=True) # Run headless (no visible browser window)
            page = browser.new_page(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            )
            logging.info(f"Navigating to {url}...")
            # Increase timeout, wait until network is idle or load state is reached
            page.goto(url, timeout=60000, wait_until='networkidle') # 60 second timeout, wait for network activity to cease
            logging.info("Page loaded, waiting for potential dynamic content...")
            # Optional: Add specific waits for elements if needed, e.g., page.wait_for_selector('.list-card', timeout=15000)
            time.sleep(random.uniform(3, 7)) # Add a random delay after load
            html_content = page.content()
            logging.info(f"Successfully fetched page content (Length: {len(html_content)}).")
            browser.close()
        except PlaywrightTimeoutError:
            logging.error(f"Timeout error while loading {url}")
            if 'browser' in locals() and browser.is_connected():
                 browser.close()
            return None
        except Exception as e:
            logging.error(f"Error fetching Zillow data using Playwright: {e}")
            if 'browser' in locals() and browser.is_connected():
                 browser.close()
            return None

    return html_content

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
            beds, baths, sqft = None, None, None # Use None for numeric conversion later
            if details_tag:
                details_items = details_tag.find_all('li')
                # This logic assumes a specific order or content pattern, adjust as needed
                for item in details_items:
                    text = item.text.lower()
                    item_value_tag = item.find('span') # Often the value is inside a span
                    item_value = item_value_tag.text.strip() if item_value_tag else item.text.strip()
                    try:
                        if 'bd' in text or 'bed' in text:
                            beds = int(item_value.split()[0].replace(',', ''))
                        elif 'ba' in text or 'bath' in text:
                            baths = float(item_value.split()[0].replace(',', ''))
                        elif 'sqft' in text or 'sq ft' in text:
                            sqft = int(item_value.split()[0].replace(',', ''))
                    except (ValueError, IndexError):
                        logging.warning(f"Could not parse numeric detail from '{item_value}' in card: {address}")


            # --- Attempt to find MLS ID and Status (NEEDS INSPECTION) ---
            # These selectors are VERY LIKELY INCORRECT. Inspect Zillow page source.
            mls_id_tag = card.find(attrs={"data-testid": "mls-id"}) # Example using data-testid
            mls_id = mls_id_tag.text.strip() if mls_id_tag else None

            status_tag = card.find('div', class_='list-card-status') # Example class
            status = status_tag.text.strip() if status_tag else 'Unknown'
            # --- End MLS ID / Status ---

            # Clean Price (remove $, commas, handle non-numeric like 'Contact agent')
            cleaned_price = None
            if price and price != 'N/A':
                 price_text = price.replace('$', '').replace(',', '').replace('+','').strip()
                 if price_text.isdigit():
                     cleaned_price = int(price_text)
                 else:
                     logging.warning(f"Could not parse price '{price}' for property: {address}")
                     status = price # If price isn't numeric, maybe it's the status?

            # Ensure MLS ID is present, otherwise skip (as it's the key)
            if not mls_id:
                logging.warning(f"Skipping property due to missing MLS ID: {address}")
                continue

            property_data = {
                # Match keys to the field names defined in new_table_fields
                'MLS ID': mls_id, # Primary Key
                'Address': address,
                'Price': cleaned_price, # Use cleaned numeric value
                'Beds': beds,
                'Baths': baths,
                'Sqft': sqft,
                'URL': url,
                'Status': status
                # 'Last Seen' will be added in send_to_airtable
            }
            properties.append(property_data)
            # logging.debug(f"Parsed property: {address}")

        except Exception as e:
            logging.warning(f"Could not parse a property card: {e}. Skipping card.")
            # logging.debug(f"Problematic card HTML snippet: {card.prettify()[:500]}...") # Log snippet for debugging
            continue

    logging.info(f"Successfully parsed {len(properties)} properties.")
    return properties


# --- Airtable Metadata API Helpers ---

BASE_META_URL = "https://api.airtable.com/v0/meta"

def _call_airtable_meta_api(token, method, endpoint, json_data=None):
    """Generic helper to call the Airtable Metadata API."""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    url = f"{BASE_META_URL}/{endpoint}"
    try:
        response = requests.request(method, url, headers=headers, json=json_data, timeout=15)
        response.raise_for_status()
        # Check for empty response which can happen on successful POST/PATCH with no content
        if response.status_code == 204 or not response.content:
            return {}
        return response.json()
    except requests.exceptions.RequestException as e:
        error_message = f"Airtable API Error ({method} {url}): {e}"
        if e.response is not None:
            try:
                error_details = e.response.json()
                err_info = error_details.get('error', {})
                msg = err_info.get('message', e.response.text) if isinstance(err_info, dict) else err_info
                error_message += f" - Status: {e.response.status_code}, Response: {msg}"
            except ValueError:
                 error_message += f" - Status: {e.response.status_code}, Response: {e.response.text[:200]}"
        logging.error(error_message)
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred calling Airtable API: {e}")
        return None

def get_base_schema(token, base_id):
    """Fetches the schema (including tables) for a given base."""
    if not token or not base_id: return None
    return _call_airtable_meta_api(token, "GET", f"bases/{base_id}/tables")

def create_airtable_table(token, base_id, table_name, fields):
    """Creates a new table in the specified base."""
    if not all([token, base_id, table_name, fields]): return None
    endpoint = f"bases/{base_id}/tables"
    payload = {
        "name": table_name,
        "fields": fields,
        # Optional: Add description?
        # "description": f"Zillow listings for ZIP code {table_name.split('_')[-1]}"
    }
    return _call_airtable_meta_api(token, "POST", endpoint, json_data=payload)

# --- End Airtable Metadata API Helpers ---
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

    # Check if table exists, create if not
    logging.info(f"Checking schema for base '{base_id}'...")
    schema_data = get_base_schema(access_token, base_id)
    if schema_data is None:
        logging.error("Failed to retrieve base schema. Cannot proceed.")
        return False

    existing_tables = {t['name']: t for t in schema_data.get('tables', [])}

    if table_name not in existing_tables:
        logging.info(f"Table '{table_name}' not found in base '{base_id}'. Attempting to create it.")
        # Define the schema for the new table
        # NOTE: Field types: singleLineText, multilineText, number, currency, percent, date, dateTime, url, email, checkbox, singleSelect, multipleSelects, singleCollaborator, multipleCollaborators
        # NOTE: For number/currency/percent, use 'options': {'precision': X} (e.g., 0 for integer, 2 for currency)
        # NOTE: Primary field MUST be 'singleLineText' or similar text-based field for table creation via API.
        new_table_fields = [
            {"name": "MLS ID", "type": "singleLineText"}, # Primary Field
            {"name": "Address", "type": "singleLineText"},
            {"name": "Price", "type": "currency", "options": {"symbol": "$", "precision": 0}},
            {"name": "Beds", "type": "number", "options": {"precision": 0}}, # Assuming whole numbers
            {"name": "Baths", "type": "number", "options": {"precision": 1}}, # Allowing half baths
            {"name": "Sqft", "type": "number", "options": {"precision": 0}},
            {"name": "URL", "type": "url"},
            {"name": "Status", "type": "singleLineText"}, # Or maybe singleSelect if statuses are known
            {"name": "Last Seen", "type": "dateTime", "options": {"dateFormat": {"name": "iso"}, "timeFormat": {"name": "24hour"}, "timeZone": "client"}} # Use client timezone
        ]
        creation_result = create_airtable_table(access_token, base_id, table_name, new_table_fields)
        if creation_result is None:
             logging.error(f"Failed to create table '{table_name}'. Cannot proceed.")
             return False
        logging.info(f"Successfully created table '{table_name}'.")
        # Short delay to allow Airtable to fully process the new table
        time.sleep(2)
    else:
        logging.info(f"Table '{table_name}' found in base '{base_id}'.")
        # TODO: Optionally check if existing table schema matches expected schema and update if needed (more complex)

    # TODO: Implement upsert logic using MLS ID as key field

    try:
        api = Api(access_token)
        # Get table object using the derived name
        table = api.table(base_id, table_name)
        logging.info(f"Connected to Airtable. Attempting to send/update {len(data)} records in table '{table_name}'.")

        # Define the key field for upsert operation
        key_field = "MLS ID" # This MUST match the primary field name defined above

        processed_count = 0
        records_to_upsert = []
        now_iso = datetime.now().isoformat() # Get current timestamp once

        for record in data:
            # Ensure the record has the key field (MLS ID) - skip if missing
            if not record.get(key_field):
                logging.warning(f"Skipping record due to missing key field '{key_field}': {record.get('Address', 'N/A')}")
                continue

            # Add/Update the 'Last Seen' timestamp
            record['Last Seen'] = now_iso

            # Prepare record for batch upsert format
            records_to_upsert.append({"fields": record})

        if not records_to_upsert:
             logging.warning("No valid records with MLS ID found to upsert.")
             # Return True because the process didn't fail, just had nothing to send
             return True

        try:
            # Perform batch upsert
            # Note: batch_upsert handles finding records by key_field and updates/creates as needed
            # It takes a list of records, each wrapped in {"fields": ...}
            # It also requires a list of key field names (just one in our case)
            results = table.batch_upsert(records_to_upsert, key_fields=[key_field])
            processed_count = len(results.get('records', [])) # Count processed records from response
            logging.info(f"Successfully processed (upserted) {processed_count}/{len(records_to_upsert)} records in Airtable table '{table_name}'.")
            # Check for potential errors within the batch operation if needed (more complex)
            # e.g., results might contain error info for specific records

            return processed_count > 0 or len(records_to_upsert) == 0 # Return True if something was processed or if there was nothing to process initially

        except Exception as e:
            logging.error(f"Error during batch upsert to Airtable table '{table_name}': {e}")
            # Consider logging the data that failed if possible
            return False

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
