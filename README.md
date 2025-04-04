# Zillow Scraper to Airtable

This project aims to scrape property listing data from Zillow for a specific ZIP code and send it to an Airtable base. It includes a web UI for configuration.

## Components

1.  **Configuration UI (`config_app.py`):** A Flask web application that allows users to:
    *   Enter their Airtable Access Token.
    *   Fetch and select an Airtable Base associated with the token.
    *   Enter the target Zillow ZIP code.
    *   Save these details to a `.env` file.
    *   Trigger the scraper script to run as a background process.
2.  **Zillow Scraper (`zillow_airtable_scraper.py`):** A Python script that:
    *   Reads configuration from the `.env` file.
    *   Constructs a Zillow search URL based on the configured ZIP code.
    *   Uses **Playwright** to launch a headless browser and fetch the Zillow page content (attempting to bypass basic anti-scraping).
    *   Attempts to parse the HTML for property listings (Address, Price, Beds, Baths, Sqft, URL, MLS ID, Status).
    *   Connects to the configured Airtable Base.
    *   Checks if a table named `ZIP_{zip_code}` exists.
    *   **Creates the table** if it doesn't exist, defining a specific schema (including `MLS ID` as the primary field).
    *   Attempts to **upsert** the scraped data into the table using the `MLS ID` as the key field to avoid duplicates and update existing entries. Adds a `Last Seen` timestamp.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/bensheed/zillow-scraper-to-airtable.git
    cd zillow-scraper-to-airtable
    ```
2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    playwright install --with-deps
    ```
3.  **Configure:** Run the configuration UI and enter your details:
    ```bash
    python config_app.py
    ```
    *   Open your browser to `http://localhost:58124`.
    *   Enter your Airtable Access Token (starting with `pat...`).
    *   Click "Fetch Bases" and select your desired Base.
    *   Enter the 5-digit ZIP code you want to scrape.
    *   Click "Save Configuration".
    *   You can stop the config app (`Ctrl+C`) after saving, or leave it running to use the "Run Scraper Now" button.

    *(Alternatively, manually create a `.env` file with `AIRTABLE_ACCESS_TOKEN`, `AIRTABLE_BASE_ID`, and `ZILLOW_ZIP_CODE`)*

## Running

1.  **Run the Config UI (Optional but recommended):**
    ```bash
    python config_app.py
    ```
    *   Access `http://localhost:58124`.
    *   After saving the configuration, a "Run Scraper Now" button will appear. Click it to start the scraper in the background.
2.  **Run the Scraper Directly (Requires `.env` file to be configured):**
    ```bash
    python zillow_airtable_scraper.py
    ```
    *   Logs from the scraper will be printed to the console and appended to `scraper_run.log`.

## Current Status & Limitations (IMPORTANT)

*   **Zillow Anti-Scraping:** Zillow employs sophisticated anti-scraping measures. While this script uses Playwright (headless browser) instead of simple requests, **Zillow currently detects this and presents a CAPTCHA page** instead of the actual listings.
*   **Scraper Failure:** Because of the CAPTCHA, the scraper currently **fails** to fetch the listing data. The `fetch_zillow_data` function returns `None`, and the script logs warnings about not finding property cards.
*   **Parsing Selectors:** The CSS selectors used in `parse_zillow_html` to find property cards, details, MLS ID, etc., are **placeholders** and **will need significant adjustment** based on the actual HTML structure *if* the CAPTCHA issue is resolved. Finding a reliable MLS ID selector is particularly important for the upsert logic.
*   **Airtable Table Creation:** The logic to automatically create the `ZIP_{zip_code}` table exists but may not have been fully tested due to the inability to scrape data. Ensure the target Airtable Base exists.

## Potential Future Development (To Overcome Blocking)

*   **Playwright Stealth:** Implement techniques to make Playwright appear less like a bot (e.g., using `playwright-stealth` or similar libraries/manual configurations).
*   **CAPTCHA Solving Services:** Integrate a third-party service (e.g., 2Captcha) to solve the CAPTCHAs presented by Zillow.
*   **Residential Proxies:** Route Playwright traffic through rotating residential proxies.

**Conclusion:** The configuration UI and the Airtable interaction logic (including table creation and upsert planning) are mostly in place, but the core Zillow scraping functionality is currently blocked by anti-bot measures (CAPTCHA). Significant further work on bypassing these measures is required for the scraper to function.