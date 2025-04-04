import os
import requests
import subprocess # Added for running scraper
import sys # Added for getting python executable
from flask import Flask, request, render_template_string, flash, redirect, url_for, session # Added session
from dotenv import load_dotenv, set_key, find_dotenv

# Find the .env file
dotenv_path = find_dotenv()
# Create .env if it doesn't exist
if not dotenv_path:
    with open(".env", "w") as f:
        f.write("# Configuration for Zillow Scraper\\n")
    dotenv_path = find_dotenv()

app = Flask(__name__)
# Required for flashing messages
app.secret_key = os.urandom(24)

# HTML template for the form
# Using render_template_string for simplicity, no separate template file needed
HTML_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
    <title>Zillow Scraper Configuration</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f0f2f5; /* Light grey background */
            color: #333;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            padding: 20px; /* Add padding for smaller screens */
            box-sizing: border-box;
        }
        .container {
            background-color: #ffffff; /* White container background */
            padding: 30px 40px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
            width: 100%; /* Use full width available */
            max-width: 600px;
            box-sizing: border-box;
        }
        h1 {
            color: #2c3e50; /* Dark blue-grey heading */
            text-align: center;
            margin-bottom: 30px;
            font-size: 1.8em;
        }
        label {
            display: block;
            margin-top: 15px;
            margin-bottom: 5px;
            font-weight: 600;
            color: #555; /* Darker grey label text */
        }
        input[type=text], input[type=url], select {
            width: 100%;
            padding: 12px;
            margin-top: 5px;
            border: 1px solid #d1d9e6; /* Light blue-grey border */
            border-radius: 6px;
            box-sizing: border-box; /* Include padding and border in element's total width and height */
            background-color: #f8f9fa; /* Very light grey input background */
            color: #333;
            font-size: 1em;
        }
        input[type=text]:focus, input[type=url]:focus, select:focus {
            border-color: #4a90e2; /* Blue border on focus */
            outline: none;
            box-shadow: 0 0 0 2px rgba(74, 144, 226, 0.2);
        }
        input[type=submit], button {
            margin-top: 25px;
            padding: 12px 20px;
            background-color: #4a90e2; /* Primary blue button */
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 1em; /* Adjusted font size */
            font-weight: 600;
            width: 100%;
            transition: background-color 0.2s ease;
            box-sizing: border-box;
        }
        input[type=submit]:hover, button:hover {
            background-color: #357abd; /* Darker blue on hover */
        }
        /* Style disabled buttons */
        button:disabled, input[type=submit]:disabled {
             background-color: #a0c4e8; /* Lighter blue when disabled */
             cursor: not-allowed;
        }
        .flash {
            padding: 12px 15px;
            margin-bottom: 20px; /* Adjusted margin */
            border-radius: 6px;
            font-size: 0.9em; /* Adjusted font size */
            text-align: center;
        }
        .flash.success {
            background-color: #e0f2f7; /* Light blue success */
            color: #0d47a1; /* Dark blue text */
            border: 1px solid #b3e5fc;
        }
        .flash.error {
            background-color: #fdecea; /* Light red error */
            color: #b71c1c; /* Dark red text */
            border: 1px solid #f8c8c8;
        }
        .hidden {
            display: none;
        }
        /* Add some spacing between form groups */
        .form-group {
            margin-bottom: 20px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Zillow Scraper Configuration</h1>
    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
                <div class="flash {{ category }}">{{ message }}</div>
            {% endfor %}
        {% endif %}
    {% endwith %}

    <!-- Conditionally show Run Scraper button -->
    {% if session.pop('show_run_button', None) %}
    <div style="margin-bottom: 20px;">
        <a href="{{ url_for('run_scraper') }}" id="run-scraper-link" style="background-color: #28a745; width: auto; display: inline-block; padding: 12px 20px; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 1em; font-weight: 600; text-decoration: none;">Run Scraper Now</a>
        <span id="run-loader" style="display: none; margin-left: 10px;">🔄 Running...</span>
    </div>
    {% endif %}
    <!-- End Run Scraper button -->

    <form method="post" id="config-form"> <!-- Main form still posts to config_page -->
        <!-- Step 1: Enter Token (JS Submit) -->
        <input type="hidden" name="action" id="form_action" value=""> <!-- Hidden field for action -->
        <div class="form-group">
            <label for="access_token">Airtable Access Token:</label>
            <input type="text" id="access_token" name="access_token" value="{{ config.AIRTABLE_ACCESS_TOKEN }}" required>
            <button type="button" id="fetch-bases-btn">Fetch Bases</button> <!-- Changed to type="button" -->
        </div>

        <!-- Step 2: Select Base (populated after fetching) -->
        <div id="base-select-div" class="form-group {{ 'hidden' if not bases }}">
            <input type="hidden" name="access_token_hidden" value="{{ config.AIRTABLE_ACCESS_TOKEN }}"> <!-- Carry token forward -->
            <label for="base_id">Select Airtable Base:</label>
            <!-- Updated onchange to set action value before submitting -->
            <select id="base_id" name="selected_base_id" onchange="document.getElementById('form_action').value = 'fetch_tables'; this.form.submit();" required>
                <option value="">-- Select a Base --</option>
                {% for base in bases %}
                    <option value="{{ base.id }}" {{ 'selected' if base.id == config.AIRTABLE_BASE_ID }}>{{ base.name }} ({{ base.id }})</option>
                {% endfor %}
            </select>
            <!-- Hidden submit button triggered by onchange, not really needed now -->
             <button type="submit" name="action" value="fetch_tables" class="hidden">Fetch Tables</button>
        </div>

        <!-- Step 3: Zillow ZIP Code and Save -->
        <!-- Table selection removed - will be determined by ZIP code -->
        <div id="final-step-div" class="form-group {{ 'hidden' if not config.AIRTABLE_BASE_ID }}"> <!-- Show only when Base is selected -->
             <input type="hidden" name="access_token_hidden_2" value="{{ config.AIRTABLE_ACCESS_TOKEN }}"> <!-- Carry token forward -->
             <input type="hidden" name="selected_base_id_hidden" value="{{ config.AIRTABLE_BASE_ID }}"> <!-- Carry base_id forward -->
            <label for="zip_code">Zillow ZIP Code (for scraping and table name):</label>
            <input type="text" id="zip_code" name="zip_code" value="{{ config.ZILLOW_ZIP_CODE }}" pattern="[0-9]{5}" title="Enter a 5-digit ZIP code" required>
            <button type="button" id="save-config-btn">Save Configuration</button>
        </div>
    </form>
    </div> <!-- Close container -->

    <script>
        document.getElementById('fetch-bases-btn').addEventListener('click', function() {
            document.getElementById('form_action').value = 'fetch_bases';
            document.getElementById('config-form').submit();
        });

        // Add listener for the Save button
        document.getElementById('save-config-btn').addEventListener('click', function() {
            document.getElementById('form_action').value = 'save_config';
            document.getElementById('config-form').action = "{{ url_for('config_page') }}"; // Ensure main form posts to config_page
            // Optional: Add basic JS validation here if needed before submitting
            document.getElementById('config-form').submit();
        });
    </script>
</body>
</html>
"""

def get_current_config():
    """Loads current configuration from .env file."""
    load_dotenv(dotenv_path=dotenv_path, override=True) # Force reload
    return {
        # Use AIRTABLE_ACCESS_TOKEN now
        "AIRTABLE_ACCESS_TOKEN": os.getenv("AIRTABLE_ACCESS_TOKEN", ""),
        "AIRTABLE_BASE_ID": os.getenv("AIRTABLE_BASE_ID", ""),
        # "AIRTABLE_TABLE_NAME": os.getenv("AIRTABLE_TABLE_NAME", ""), # Removed Table Name
        "ZILLOW_ZIP_CODE": os.getenv("ZILLOW_ZIP_CODE", "")
    }

# --- Airtable API Helper Functions ---
def get_airtable_metadata(token, endpoint):
    """Generic function to call Airtable Metadata API."""
    headers = {"Authorization": f"Bearer {token}"}
    url = f"https://api.airtable.com/v0/meta/{endpoint}"
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        error_message = f"Error calling Airtable Metadata API ({endpoint}): {e}"
        if e.response is not None:
            try:
                error_details = e.response.json()
                # Try to extract specific error message or type
                err_info = error_details.get('error', {})
                if isinstance(err_info, dict):
                    msg = err_info.get('message', e.response.text)
                    err_type = err_info.get('type')
                    if err_type:
                         msg = f"[{err_type}] {msg}"
                else: # Sometimes error is just a string
                    msg = err_info or e.response.text
                error_message += f" - {msg}"

            except ValueError: # If response is not JSON
                 error_message += f" - Status: {e.response.status_code}, Response: {e.response.text[:200]}"
        flash(error_message, 'error')
        return None
    except Exception as e: # Catch other potential errors
        flash(f"An unexpected error occurred: {e}", 'error')
        return None

def get_airtable_bases(token):
    """Fetches list of bases accessible by the token."""
    if not token: return []
    data = get_airtable_metadata(token, "bases")
    return data.get('bases', []) if data else []

def get_airtable_tables(token, base_id):
    """Fetches list of tables for a given base."""
    if not token or not base_id: return []
    data = get_airtable_metadata(token, f"bases/{base_id}/tables")
    return data.get('tables', []) if data else []
# --- End Airtable API Helpers ---


@app.route('/', methods=['GET', 'POST'])
def config_page():
    config = get_current_config()
    bases = []
    # tables = [] # Removed tables list
    action = request.form.get('action')

    # Preserve state across POST requests using form data
    access_token = request.form.get('access_token') or request.form.get('access_token_hidden') or request.form.get('access_token_hidden_2') or config.get('AIRTABLE_ACCESS_TOKEN')
    selected_base_id = request.form.get('selected_base_id') or request.form.get('selected_base_id_hidden') or config.get('AIRTABLE_BASE_ID')
    # selected_table_name = request.form.get('selected_table_name') or config.get('AIRTABLE_TABLE_NAME') # Removed table name
    zip_code = request.form.get('zip_code') or config.get('ZILLOW_ZIP_CODE')

    # Update config dict with potentially submitted values for re-rendering the form state correctly
    config['AIRTABLE_ACCESS_TOKEN'] = access_token
    config['AIRTABLE_BASE_ID'] = selected_base_id
    # config['AIRTABLE_TABLE_NAME'] = selected_table_name # Removed table name
    config['ZILLOW_ZIP_CODE'] = zip_code

    if request.method == 'POST':
        if action == 'fetch_bases':
            if access_token:
                bases = get_airtable_bases(access_token)
                if bases is None: bases = [] # API call failed, error flashed in helper
                # Clear subsequent selections if we re-fetch bases
                config['AIRTABLE_BASE_ID'] = ""
                config['AIRTABLE_TABLE_NAME'] = ""
                selected_base_id = ""
                selected_table_name = ""
                tables = [] # Clear tables list
            else:
                flash("Please enter an Airtable Access Token.", "error")

        # 'fetch_tables' action removed as table is now dynamic

        elif action == 'save_config':
            # Final save action - retrieve values from the *correct* hidden fields or inputs
            token_to_save = request.form.get('access_token_hidden_2') or request.form.get('access_token_hidden') or request.form.get('access_token')
            base_id_to_save = request.form.get('selected_base_id_hidden') or request.form.get('selected_base_id')
            # table_name_to_save = request.form.get('selected_table_name') # Removed table name
            zip_code_to_save = request.form.get('zip_code')

            # Basic validation - removed table_name_to_save
            if token_to_save and base_id_to_save and zip_code_to_save:
                # Add ZIP code validation (basic 5 digits)
                if not (zip_code_to_save and zip_code_to_save.isdigit() and len(zip_code_to_save) == 5):
                     flash('Invalid ZIP Code format. Please enter 5 digits.', 'error')
                     # Repopulate bases if save fails
                     if access_token: bases = get_airtable_bases(access_token)
                     # No tables to repopulate
                else:
                    try:
                        # Save to .env file - removed AIRTABLE_TABLE_NAME
                        set_key(dotenv_path, "AIRTABLE_ACCESS_TOKEN", token_to_save)
                        set_key(dotenv_path, "AIRTABLE_BASE_ID", base_id_to_save)
                        # set_key(dotenv_path, "AIRTABLE_TABLE_NAME", table_name_to_save) # Removed
                        set_key(dotenv_path, "ZILLOW_ZIP_CODE", zip_code_to_save)
                        flash('Configuration saved successfully!', 'success')
                        session['show_run_button'] = True # Set flag to show button after redirect
                        # Redirect to GET to show the final saved state cleanly and prevent resubmission
                        return redirect(url_for('config_page'))
                    except Exception as e:
                        flash(f'Error saving configuration: {e}', 'error')
                        # Repopulate bases if save fails
                        if access_token: bases = get_airtable_bases(access_token)
                        # No tables to repopulate
            # This else corresponds to the 'if token_to_save and ...'
            else:
                 flash('Missing required fields for saving. Ensure Base and ZIP Code are selected and valid.', 'error') # Updated message
                 # Repopulate bases if save fails due to missing fields
                 if access_token: bases = get_airtable_bases(access_token)
                 # No tables to repopulate

        # If it's a POST but not 'fetch_bases' or 'save_config', and base wasn't just selected,
        # it might be an intermediate state (e.g., table selected). We still need to populate bases/tables.
        elif access_token:
             bases = get_airtable_bases(access_token)
             if bases is None: bases = []
             if selected_base_id:
                 tables = get_airtable_tables(access_token, selected_base_id)
                 if tables is None: tables = []


    # For GET request: Load config and potentially pre-fetch bases if token exists
    elif request.method == 'GET':
         if config.get('AIRTABLE_ACCESS_TOKEN'):
             bases = get_airtable_bases(config['AIRTABLE_ACCESS_TOKEN'])
             if bases is None: bases = []
             # Clear saved Base ID if it's no longer valid for the current token
             if config.get('AIRTABLE_BASE_ID') and not any(b['id'] == config['AIRTABLE_BASE_ID'] for b in bases):
                 config['AIRTABLE_BASE_ID'] = ""
                 set_key(dotenv_path, "AIRTABLE_BASE_ID", "") # Clear from .env too
                 # Also clear ZIP code if Base becomes invalid? Optional, maybe keep it.
                 # config['ZILLOW_ZIP_CODE'] = ""
                 # set_key(dotenv_path, "ZILLOW_ZIP_CODE", "")


    # Ensure bases list is valid
    if bases is None: bases = []
    # tables variable removed

    # Pass show_run_button flag from session to template
    show_run_button = session.get('show_run_button', False)

    return render_template_string(HTML_TEMPLATE, config=config, bases=bases, show_run_button=show_run_button) # Removed tables
@app.route('/run_scraper', methods=['GET']) # Keep as GET
def run_scraper():
    """Triggers the scraper script as a background process."""
    try:
        # Ensure config is saved before running
        config = get_current_config()
        # Updated check: Removed AIRTABLE_TABLE_NAME
        if not all([config.get("AIRTABLE_ACCESS_TOKEN"), config.get("AIRTABLE_BASE_ID"), config.get("ZILLOW_ZIP_CODE")]):
             flash("Configuration is incomplete (missing Token, Base ID, or ZIP Code). Please save configuration before running.", "error")
             return redirect(url_for('config_page'))

        # Updated check: Removed AIRTABLE_TABLE_NAME
        if "YOUR_" in config.get("AIRTABLE_ACCESS_TOKEN", "") or not config.get("AIRTABLE_ACCESS_TOKEN", "").startswith("pat") \
           or "YOUR_" in config.get("AIRTABLE_BASE_ID", "") \
           or not (config.get("ZILLOW_ZIP_CODE", "").isdigit() and len(config.get("ZILLOW_ZIP_CODE", "")) == 5):
             flash("Placeholder values or invalid token/Base ID/ZIP code format detected in .env file. Please correct configuration.", "error")
             return redirect(url_for('config_page'))

        # Get the path to the current python interpreter
        python_executable = sys.executable
        scraper_script = os.path.join(os.path.dirname(__file__), 'zillow_airtable_scraper.py')
        # Use Popen for non-blocking execution
        # Redirect stdout/stderr to a log file for the scraper process
        log_path = os.path.join(os.path.dirname(__file__), 'scraper_run.log')
        with open(log_path, "a") as log_file:
             process = subprocess.Popen([python_executable, scraper_script], stdout=log_file, stderr=subprocess.STDOUT)
        flash(f"Scraper process initiated (PID: {process.pid}). Check terminal or scraper_run.log for logs.", "success")
        session['show_run_button'] = False # Hide button after starting
    except Exception as e:
        flash(f"Error starting scraper process: {e}", "error")

    return redirect(url_for('config_page'))



if __name__ == '__main__':
    # Make accessible on the network, choose a port (e.g., 58124)
    # Use 0.0.0.0 to allow external connections within the container/network
    app.run(host='0.0.0.0', port=58124, debug=True)