import os
from flask import Flask, request, render_template_string, flash, redirect, url_for
from dotenv import load_dotenv, set_key, find_dotenv

# Find the .env file
dotenv_path = find_dotenv()
# Create .env if it doesn't exist
if not dotenv_path:
    with open(".env", "w") as f:
        f.write("# Configuration for Zillow Scraper\n")
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
        body { font-family: sans-serif; margin: 20px; }
        label { display: block; margin-top: 10px; font-weight: bold; }
        input[type=text], input[type=url] { width: 90%; max-width: 500px; padding: 8px; margin-top: 5px; border: 1px solid #ccc; border-radius: 4px; }
        input[type=submit] { margin-top: 20px; padding: 10px 15px; background-color: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer; }
        input[type=submit]:hover { background-color: #0056b3; }
        .flash { padding: 10px; margin-top: 15px; border-radius: 4px; }
        .flash.success { background-color: #d4edda; color: #155724; border: 1px solid #c3e6cb; }
        .flash.error { background-color: #f8d7da; color: #721c24; border: 1px solid #f5c6cb; }
    </style>
</head>
<body>
    <h1>Zillow Scraper Configuration</h1>
    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
                <div class="flash {{ category }}">{{ message }}</div>
            {% endfor %}
        {% endif %}
    {% endwith %}
    <form method="post">
        <label for="api_key">Airtable API Key:</label>
        <input type="text" id="api_key" name="api_key" value="{{ config.AIRTABLE_API_KEY }}" required>

        <label for="base_id">Airtable Base ID:</label>
        <input type="text" id="base_id" name="base_id" value="{{ config.AIRTABLE_BASE_ID }}" required>

        <label for="table_name">Airtable Table Name:</label>
        <input type="text" id="table_name" name="table_name" value="{{ config.AIRTABLE_TABLE_NAME }}" required>

        <label for="zillow_url">Zillow Search URL:</label>
        <input type="url" id="zillow_url" name="zillow_url" value="{{ config.ZILLOW_SEARCH_URL }}" required>

        <input type="submit" value="Save Configuration">
    </form>
</body>
</html>
"""

def get_current_config():
    """Loads current configuration from .env file."""
    load_dotenv(dotenv_path=dotenv_path, override=True) # Force reload
    return {
        "AIRTABLE_API_KEY": os.getenv("AIRTABLE_API_KEY", ""),
        "AIRTABLE_BASE_ID": os.getenv("AIRTABLE_BASE_ID", ""),
        "AIRTABLE_TABLE_NAME": os.getenv("AIRTABLE_TABLE_NAME", ""),
        "ZILLOW_SEARCH_URL": os.getenv("ZILLOW_SEARCH_URL", "")
    }

@app.route('/', methods=['GET', 'POST'])
def config_page():
    if request.method == 'POST':
        try:
            # Update .env file
            set_key(dotenv_path, "AIRTABLE_API_KEY", request.form['api_key'])
            set_key(dotenv_path, "AIRTABLE_BASE_ID", request.form['base_id'])
            set_key(dotenv_path, "AIRTABLE_TABLE_NAME", request.form['table_name'])
            set_key(dotenv_path, "ZILLOW_SEARCH_URL", request.form['zillow_url'])
            flash('Configuration saved successfully!', 'success')
        except Exception as e:
            flash(f'Error saving configuration: {e}', 'error')
        # Redirect to GET to prevent form resubmission on refresh
        return redirect(url_for('config_page'))

    # For GET request, load current config and render form
    current_config = get_current_config()
    return render_template_string(HTML_TEMPLATE, config=current_config)

if __name__ == '__main__':
    # Make accessible on the network, choose a port (e.g., 58124)
    # Use 0.0.0.0 to allow external connections within the container/network
    app.run(host='0.0.0.0', port=58124, debug=True)