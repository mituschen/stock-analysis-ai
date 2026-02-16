"""Flask web application for the stock analysis AI.

This module wires together the prompt loader, AI client and database to provide
a simple web interface for running analyses.  Visit the root URL to enter a
stock ticker symbol.  After submitting, the app will process each prompt and
display the results.
"""

import json
from collections import Counter
from pathlib import Path
from typing import Dict, Any, List, Tuple

from flask import Flask, render_template, request

from models import database
from models.prompt_loader import load_prompts, Prompt
from models.ai_client import AIClient


app = Flask(__name__)

# Initialize database on startup
database.init_db()

# Instantiate AI client once
ai_client = AIClient()


def load_context(ticker: str) -> Dict[str, Any]:
    """Load or construct the analysis context for a ticker.

    This function currently returns a simple context containing only the ticker
    symbol.  Extend this function to pull in historical price data,
    fundamentals, news, etc.  The context object will be passed to your
    prompts as the `context` variable.
    """
    return {"ticker": ticker}


def run_analysis(ticker: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """Run all active prompts against a ticker.

    Returns a tuple `(results, summary)`.  `results` is a list of per‑prompt
    dictionaries suitable for display.  `summary` contains aggregated
    metrics (average score, final rating, final target price).
    """
    context = load_context(ticker)
    context_json = json.dumps(context)

    # Load prompt definitions from the prompts directory
    prompts_dir = Path(__file__).resolve().parent / "prompts"
    prompts: List[Prompt] = load_prompts(prompts_dir)
    if not prompts:
        raise RuntimeError("No prompt definitions found in the prompts directory.")

    # Start run in database
    run_id = database.start_run(ticker, context_json)

    result_entries: List[Dict[str, Any]] = []
    scores: List[int] = []
    ratings: List[str] = []
    targets: List[float] = []

    for prompt in prompts:
        parsed_data, raw_text = ai_client.generate(prompt, context)
        score = int(parsed_data.get("score", 0))
        rating = str(parsed_data.get("rating", "")).upper()
        target_price = float(parsed_data.get("target_buy_price", 0))
        rationale = parsed_data.get("rationale", "")
        # Save individual prompt result
        database.save_prompt_result(
            run_id,
            prompt.prompt_id,
            prompt.version,
            prompt.name,
            score,
            rating,
            target_price,
            rationale,
            raw_text,
        )
        # Collect for summary
        scores.append(score)
        ratings.append(rating)
        targets.append(target_price)
        # Prepare entry for display
        result_entries.append(
            {
                "prompt_id": prompt.prompt_id,
                "prompt_name": prompt.name,
                "prompt_version": prompt.version,
                "score": score,
                "rating": rating,
                "target_buy_price": target_price,
                "rationale": rationale,
            }
        )

    # Compute aggregated metrics
    average_score = sum(scores) / len(scores)
    # Determine final rating based on majority vote; if tie, choose HOLD
    rating_counts = Counter(ratings)
    most_common = rating_counts.most_common()
    if len(most_common) == 1:
        final_rating = most_common[0][0]
    else:
        # If tie for top counts, default to HOLD
        if len(most_common) >= 2 and most_common[0][1] == most_common[1][1]:
            final_rating = "HOLD"
        else:
            final_rating = most_common[0][0]
    final_target_price = sum(targets) / len(targets)

    # Finish run in database
    database.finish_run(run_id, average_score, final_rating, final_target_price)

    summary = {
        "average_score": average_score,
        "final_rating": final_rating,
        "final_target_price": final_target_price,
    }
    return result_entries, summary


@app.route("/", methods=["GET", "POST"])
def index():
    """Home page with form to enter a stock ticker and view results."""
    results = None
    summary = None
    ticker = None
    error = None
    if request.method == "POST":
        ticker = request.form.get("ticker", "").strip().upper()
        if not ticker:
            error = "Please enter a stock ticker."
        else:
            try:
                results, summary = run_analysis(ticker)
            except Exception as exc:
                error = str(exc)
    return render_template(
        "index.html",
        results=results,
        summary=summary,
        ticker=ticker,
        error=error,
    )


if __name__ == "__main__":
    # Run the Flask development server
    app.run(debug=True)
