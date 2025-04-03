import os
import requests
from flask import Flask, request, render_template_string, flash, redirect, url_for
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
    <form method="post" id="config-form">
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
            <select id="base_id" name="selected_base_id" onchange="this.form.action='{{ url_for('config_page') }}'; this.form.submit();" required>
                <option value="">-- Select a Base --</option>
                {% for base in bases %}
                    <option value="{{ base.id }}" {{ 'selected' if base.id == config.AIRTABLE_BASE_ID }}>{{ base.name }} ({{ base.id }})</option>
                {% endfor %}
            </select>
            <!-- Hidden submit button triggered by onchange, not really needed now -->
             <button type="submit" name="action" value="fetch_tables" class="hidden">Fetch Tables</button>
        </div>

        <!-- Step 3: Select Table (populated after selecting base) -->
        <div id="table-select-div" class="form-group {{ 'hidden' if not tables }}">
             <input type="hidden" name="access_token_hidden_2" value="{{ config.AIRTABLE_ACCESS_TOKEN }}"> <!-- Carry token forward -->
             <input type="hidden" name="selected_base_id_hidden" value="{{ config.AIRTABLE_BASE_ID }}"> <!-- Carry base_id forward -->
            <label for="table_name">Select Airtable Table:</label>
            <select id="table_name" name="selected_table_name" required>
                 <option value="">-- Select a Table --</option>
                {% for table in tables %}
                    <option value="{{ table.name }}" {{ 'selected' if table.name == config.AIRTABLE_TABLE_NAME }}>{{ table.name }}</option>
                {% endfor %}
            </select>
        </div>

        <!-- Step 4: Zillow URL and Save -->
        <div id="final-step-div" class="form-group {{ 'hidden' if not tables }}"> <!-- Show only when tables are loaded -->
            <label for="zillow_url">Zillow Search URL:</label>
            <input type="url" id="zillow_url" name="zillow_url" value="{{ config.ZILLOW_SEARCH_URL }}" required>
            <input type="submit" name="action" value="save_config" value="Save Configuration">
        </div>
    </form>
    </div> <!-- Close container -->

    <script>
        document.getElementById('fetch-bases-btn').addEventListener('click', function() {
            document.getElementById('form_action').value = 'fetch_bases';
            document.getElementById('config-form').submit();
        });
        // We might need similar logic for the final save button if this works
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
        "AIRTABLE_TABLE_NAME": os.getenv("AIRTABLE_TABLE_NAME", ""),
        "ZILLOW_SEARCH_URL": os.getenv("ZILLOW_SEARCH_URL", "")
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
    # --- DEBUG PRINT ---
    print(f"Request Method: {request.method}, Action Form Value: {request.form.get('action')}")
    # --- END DEBUG ---
    config = get_current_config()
    bases = []
    tables = []
    action = request.form.get('action')

    # Preserve state across POST requests using form data
    access_token = request.form.get('access_token') or request.form.get('access_token_hidden') or request.form.get('access_token_hidden_2') or config.get('AIRTABLE_ACCESS_TOKEN')
    selected_base_id = request.form.get('selected_base_id') or request.form.get('selected_base_id_hidden') or config.get('AIRTABLE_BASE_ID')
    selected_table_name = request.form.get('selected_table_name') or config.get('AIRTABLE_TABLE_NAME')
    zillow_url = request.form.get('zillow_url') or config.get('ZILLOW_SEARCH_URL')

    # Update config dict with potentially submitted values for re-rendering the form state correctly
    config['AIRTABLE_ACCESS_TOKEN'] = access_token
    config['AIRTABLE_BASE_ID'] = selected_base_id
    config['AIRTABLE_TABLE_NAME'] = selected_table_name
    config['ZILLOW_SEARCH_URL'] = zillow_url

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

        # This handles the implicit submission from the base dropdown's onchange event.
        # We check if selected_base_id is present in the form data (meaning it was just selected or carried over)
        # and ensure we are not in the middle of saving.
        elif 'selected_base_id' in request.form and selected_base_id and access_token and action != 'save_config':
             # Need to fetch bases again to keep the dropdown populated correctly
             bases = get_airtable_bases(access_token)
             if bases is None: bases = []

             tables = get_airtable_tables(access_token, selected_base_id)
             if tables is None: tables = []
             # Clear table selection when base changes
             config['AIRTABLE_TABLE_NAME'] = ""
             selected_table_name = ""

        elif action == 'save_config':
            # Final save action - retrieve values from the *correct* hidden fields or inputs
            token_to_save = request.form.get('access_token_hidden_2') or request.form.get('access_token_hidden') or request.form.get('access_token')
            base_id_to_save = request.form.get('selected_base_id_hidden') or request.form.get('selected_base_id')
            table_name_to_save = request.form.get('selected_table_name')
            zillow_url_to_save = request.form.get('zillow_url')

            # Basic validation
            if token_to_save and base_id_to_save and table_name_to_save and zillow_url_to_save:
                try:
                    # Save to .env file
                    # Note: Using AIRTABLE_ACCESS_TOKEN now instead of AIRTABLE_API_KEY
                    set_key(dotenv_path, "AIRTABLE_ACCESS_TOKEN", token_to_save)
                    set_key(dotenv_path, "AIRTABLE_BASE_ID", base_id_to_save)
                    set_key(dotenv_path, "AIRTABLE_TABLE_NAME", table_name_to_save)
                    set_key(dotenv_path, "ZILLOW_SEARCH_URL", zillow_url_to_save)
                    flash('Configuration saved successfully!', 'success')
                    # Redirect to GET to show the final saved state cleanly and prevent resubmission
                    return redirect(url_for('config_page'))
                except Exception as e:
                    flash(f'Error saving configuration: {e}', 'error')
                    # Repopulate if save fails
                    if access_token: bases = get_airtable_bases(access_token)
                    if access_token and selected_base_id: tables = get_airtable_tables(access_token, selected_base_id)
            else:
                 flash('Missing required fields for saving. Ensure Base and Table are selected.', 'error')
                 # Repopulate if save fails due to missing fields
                 if access_token: bases = get_airtable_bases(access_token)
                 if access_token and selected_base_id: tables = get_airtable_tables(access_token, selected_base_id)

        # If it's a POST but not 'fetch_bases' or 'save_config', and base wasn't just selected,
        # it might be an intermediate state (e.g., table selected). We still need to populate bases/tables.
        elif access_token:
             bases = get_airtable_bases(access_token)
             if bases is None: bases = []
             if selected_base_id:
                 tables = get_airtable_tables(access_token, selected_base_id)
                 if tables is None: tables = []


    # For GET request: Load config and potentially pre-fetch if token/base_id exist in .env
    elif request.method == 'GET':
         if config.get('AIRTABLE_ACCESS_TOKEN'):
             bases = get_airtable_bases(config['AIRTABLE_ACCESS_TOKEN'])
             if bases is None: bases = []
             if config.get('AIRTABLE_BASE_ID'):
                 # Ensure the saved base_id is still valid for the token
                 if any(b['id'] == config['AIRTABLE_BASE_ID'] for b in bases):
                     tables = get_airtable_tables(config['AIRTABLE_ACCESS_TOKEN'], config['AIRTABLE_BASE_ID'])
                     if tables is None: tables = []
                 else: # Saved base_id not found for this token, clear it
                     config['AIRTABLE_BASE_ID'] = ""
                     config['AIRTABLE_TABLE_NAME'] = ""
                     set_key(dotenv_path, "AIRTABLE_BASE_ID", "") # Clear from .env too
                     set_key(dotenv_path, "AIRTABLE_TABLE_NAME", "")


    # Ensure bases and tables are lists even if None was returned from API calls
    if bases is None: bases = []
    if tables is None: tables = []

    return render_template_string(HTML_TEMPLATE, config=config, bases=bases, tables=tables)


if __name__ == '__main__':
    # Make accessible on the network, choose a port (e.g., 58124)
    # Use 0.0.0.0 to allow external connections within the container/network
    app.run(host='0.0.0.0', port=58124, debug=True)