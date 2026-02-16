"""Utilities for loading prompt definitions from YAML files."""

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Dict, Any

import yaml


@dataclass
class Prompt:
    prompt_id: str
    name: str
    version: int
    template: str
    schema: Optional[Dict[str, Any]]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Prompt":
        """Construct a Prompt from a dictionary.

        Expects keys: `prompt_id`, `name`, `version`, `template`.  The `schema`
        key is optional and can be any JSON‑serialisable structure (usually a
        JSON Schema).
        """
        required = ["prompt_id", "name", "version", "template"]
        for key in required:
            if key not in data:
                raise ValueError(f"Missing required key '{key}' in prompt definition")
        return cls(
            prompt_id=str(data["prompt_id"]),
            name=str(data["name"]),
            version=int(data["version"]),
            template=str(data["template"]),
            schema=data.get("schema"),
        )


def load_prompts(directory: Path) -> List[Prompt]:
    """Load all YAML prompt files from a directory.

    Args:
        directory: Path to the folder containing `.yaml` or `.yml` files.

    Returns:
        A list of Prompt objects sorted by filename.  Files that fail to parse
        or validate are skipped with an exception printed to the console.
    """
    prompts: List[Prompt] = []
    if not directory.exists():
        return prompts
    for file in sorted(directory.glob("*.yml")) + sorted(directory.glob("*.yaml")):
        try:
            with file.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if not isinstance(data, dict):
                raise ValueError(f"YAML file {file.name} must contain a mapping at top level")
            # If a template_file is specified, read its contents relative to directory
            template_file = data.get("template_file")
            if template_file:
                template_path = directory / template_file
                if not template_path.exists():
                    raise FileNotFoundError(
                        f"Template file '{template_file}' referenced in {file.name} does not exist"
                    )
                with template_path.open("r", encoding="utf-8") as tf:
                    data["template"] = tf.read()
            prompt = Prompt.from_dict(data)
            prompts.append(prompt)
        except Exception as exc:
            print(f"Error loading prompt from {file}: {exc}")
    return prompts
