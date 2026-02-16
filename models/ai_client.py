"""Simple AI client wrapper.

This module is responsible for taking a prompt template and context, sending it to
a language model, and returning structured data.  By default it uses a
placeholder implementation that returns random values.  To enable real
language‑model inference, set the `OPENAI_API_KEY` environment variable and
fill in the OpenAI call where indicated.
"""

from __future__ import annotations

import json
import os
import random
from typing import Dict, Any, Tuple

try:
    import openai  # type: ignore
except ImportError:
    openai = None  # Optional dependency

from jsonschema import validate, ValidationError  # type: ignore
from jinja2 import Template  # type: ignore

from .prompt_loader import Prompt


class AIClient:
    """Language model client.

    The `generate` method renders the prompt template with context and returns
    a tuple `(parsed_data, raw_text)`.  `parsed_data` is a Python dict with
    `score`, `rating`, `target_buy_price` and `rationale`.  `raw_text` is the
    original text returned by the model (usually JSON).
    """

    def __init__(self) -> None:
        self.api_key = os.getenv("OPENAI_API_KEY")
        if self.api_key and openai is not None:
            openai.api_key = self.api_key
        self.llm_available = bool(self.api_key and openai is not None)

    def _render_template(self, template_str: str, context: Dict[str, Any]) -> str:
        """Render a prompt template using Jinja2.

        The context is passed under the variable name `context` so that you can
        write `{{ context }}` in your YAML templates.  Jinja2 will convert
        dictionaries to their string representation; if you prefer JSON, call
        `json.dumps(context)` in your template.
        """
        template = Template(template_str)
        return template.render(context=context)

    def _call_openai(self, rendered_prompt: str) -> str:
        """Call the OpenAI API with the rendered prompt.

        This method returns the raw response text.  Adjust the model name,
        temperature and other parameters as needed.  Note that rate limiting
        and retries are not implemented here.
        """
        assert openai is not None  # for type checkers
        # Use ChatGPT (GPT‑4) via the ChatCompletion API.  Adjust the model name
        # if necessary (e.g. "gpt-4", "gpt-4-turbo", or "gpt-3.5-turbo").
        response = openai.ChatCompletion.create(
            model="gpt-4",  # default to ChatGPT (GPT‑4)
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a helpful financial analyst. When given a prompt, "
                        "you return a JSON object with the keys: score (1–100), rating "
                        "(BUY/HOLD/SELL), target_buy_price, and rationale."
                    ),
                },
                {"role": "user", "content": rendered_prompt},
            ],
            temperature=0.0,
        )
        # Extract the assistant's reply
        return response.choices[0].message.content.strip()

    def generate(self, prompt: Prompt, context: Dict[str, Any]) -> Tuple[Dict[str, Any], str]:
        """Generate a result for a given prompt and context.

        Args:
            prompt: The Prompt object containing template and schema.
            context: A dictionary with the runtime context (e.g. stock data).

        Returns:
            A tuple `(parsed_data, raw_text)` where `parsed_data` is a Python
            dict with keys `score`, `rating`, `target_buy_price` and
            `rationale`, and `raw_text` is the raw string returned by the
            language model (which may be JSON or plain text).
        """
        rendered = self._render_template(prompt.template, {"context": context})

        if self.llm_available:
            try:
                raw_text = self._call_openai(rendered)
            except Exception as exc:
                # Fallback to stub if API call fails
                raw_text = None
        else:
            raw_text = None

        parsed: Dict[str, Any]
        if raw_text:
            # Try to parse JSON from the raw text.  If parsing fails,
            # leave parsed as an empty dict and rely on stub.
            try:
                parsed = json.loads(raw_text)
            except json.JSONDecodeError:
                parsed = {}
        else:
            parsed = {}

        # If we don't have parsed data, produce a stub.
        if not parsed:
            score = random.randint(1, 100)
            rating = (
                "BUY" if score >= 70 else "HOLD" if score >= 40 else "SELL"
            )
            target_price = round(random.uniform(10.0, 200.0), 2)
            rationale = (
                "This is a placeholder response. Replace AIClient.generate with a real model call."
            )
            parsed = {
                "score": score,
                "rating": rating,
                "target_buy_price": target_price,
                "rationale": rationale,
            }
            raw_text = json.dumps(parsed)

        # Validate against schema if provided
        if prompt.schema:
            try:
                validate(parsed, prompt.schema)
            except ValidationError as exc:
                # If validation fails, you might choose to handle it here.
                # For now we simply print a warning and proceed with parsed data.
                print(f"Warning: validation failed for prompt {prompt.prompt_id}: {exc}")

        return parsed, raw_text
