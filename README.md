# Stock Analysis AI

This repository provides a modular scaffold for a stock analysis application driven by large language models.  The goal is to make it easy to plug in your own prompts and experiment with different prompt sets while maintaining reproducibility and data persistence.  The application consists of a small Python backend and a simple web interface served via Flask.

## Features

* **File‑based prompts** – All prompts live in the `prompts/` directory.  Most prompts are defined as `.yaml` files, each specifying a `prompt_id`, `name`, `version` and either a direct `template` string or a `template_file` pointing to a separate `.txt` file.  This allows you to keep very long prompt instructions in standalone text files.  To add a new prompt you can drop a YAML (and optional text) file into the folder – the application will pick it up automatically.
* **Web UI** – A minimal front end built with Flask and Jinja2 allows you to enter a stock ticker symbol.  When you submit the form, the backend runs all active prompts against the supplied ticker (and any other context) and displays the results.  Results include a score (1–100), a rating (BUY/HOLD/SELL) and a target buy price for each prompt.
* **Database logging** – Each run is recorded in a SQLite database.  The `results` table stores one row per prompt invocation including the timestamp, prompt version used, and the raw model output.  This makes it straightforward to trace how different prompt versions performed over time.
* **Modular design** – The code is deliberately split into smaller modules (`models/database.py`, `models/prompt_loader.py`, `models/ai_client.py`) so that you can swap out the language model client or the persistence layer with minimal changes.

## Project Structure

```
stock_analysis_ai/
├── app.py               # Flask application and route definitions
├── requirements.txt      # Python package dependencies
├── models/
│   ├── __init__.py
│   ├── database.py       # Database schema and helper functions
│   ├── prompt_loader.py  # Utilities to load and validate YAML prompts
│   └── ai_client.py      # Thin wrapper around the OpenAI API (ChatGPT) with stub fallback
├── prompts/
│   ├── prompt1.yaml       # YAML wrapper referencing the large Prompt1 specification
│   └── Prompt1.txt        # Full text of Prompt 1 used by the YAML wrapper
├── templates/
│   └── index.html        # Web page template
├── static/
│   └── style.css         # Minimal styling for the page
└── README.md             # This file
```

## Getting Started

### Prerequisites

* **Python 3.8+** – The code is written for Python 3.8 and later.
* **A valid API key for your chosen language model provider** – The default implementation expects an `OPENAI_API_KEY` environment variable.  You can replace the logic in `models/ai_client.py` with any other service.

### Installation

1. Clone this repository to your local machine:

   ```bash
   git clone https://github.com/yourusername/stock_analysis_ai.git
   cd stock_analysis_ai
   ```

2. Create a virtual environment and install dependencies:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. Set your API key as an environment variable (replace with your key):

   ```bash
   export OPENAI_API_KEY="sk-your-api-key-here"
   ```

### Running the application

Start the Flask development server:

```bash
python app.py
```

Visit `http://localhost:5000` in your browser.  Enter a stock ticker (e.g. `AAPL`) and submit.  The application will load the prompts under `prompts/`, call the AI client for each, and display the results.

### Managing prompts

Prompts live in individual YAML files in the `prompts/` directory.  A sample file looks like this:

```yaml
prompt_id: value_investing_v1
name: Value Investing Check
version: 1
template: |
  You are a financial analyst specialising in value investing.  Given the following stock context, provide a score from 1 to 100 (where 70–100 is a BUY, 40–70 is a HOLD, and 1–40 is a SELL) and a target buy price.  Also briefly justify your rating.
  
  Context:
  {{ context }}

schema:
  type: object
  properties:
    score:
      type: integer
      minimum: 1
      maximum: 100
    rating:
      type: string
    target_buy_price:
      type: number
    rationale:
      type: string
  required: [score, rating, target_buy_price, rationale]
```

* `prompt_id` – A unique identifier used to track which prompt produced a result.
* `name` – Human‑friendly name.
* `version` – The version number (increment when you modify the template).
* `template` – The actual text sent to the language model.  The double braces (`{{ context }}`) indicate where runtime variables will be injected.
* `schema` – A JSON Schema used to validate the model output.  Feel free to adjust or omit depending on your needs.

To add a new prompt, drop another `.yaml` file into this folder.  The application will automatically pick it up the next time it runs.

### Storing results

Each run generates a UUID and stores results in `results.db` (a SQLite database).  The `models/database.py` module defines two tables:

* `runs` – A summary row per ticker analysis, including the start and end timestamps, the average score, final rating and target price.
* `prompt_results` – One row per prompt invocation, including the prompt ID, version, raw model response, and derived fields (score, rating, target buy price).

You can query the database with any SQLite tool or migrate to another database by replacing `database.py`.

### Deploying to GitHub

This repository does not run on GitHub Pages because it requires a Python backend.  However, you can host the code on GitHub and deploy it to a platform that supports Python applications (e.g. Fly.io, Render, Heroku, AWS Elastic Beanstalk).  A typical deployment pipeline would:

1. Push your repository to GitHub.
2. Configure your chosen platform to build the application from `requirements.txt`.
3. Set the `OPENAI_API_KEY` environment variable in your platform’s settings.
4. Start the Flask server (`python app.py` or use a production WSGI server like Gunicorn).

If you wish to use GitHub Actions to automatically deploy, consider adding a `.github/workflows/deploy.yml` file with the appropriate steps for your platform.

## Next Steps

* **Implement your prompts** – Add or replace YAML files in `prompts/` according to your analysis strategies.
* **Enhance the UI** – The current web interface is intentionally minimal.  You can extend it with charts, tables or interactive graphics using your favourite frontend framework.
* **Integrate real data** – The `context` passed to your prompts is currently a simple dictionary with only the ticker symbol.  Expand this to include historical prices, financial ratios, news summaries or any other relevant data.
* **Model upgrades** – Replace the stub in `models/ai_client.py` with actual calls to your preferred language model, and add error handling, retries and fallback prompts as needed.

Feel free to adapt and extend the structure to suit your specific needs.
