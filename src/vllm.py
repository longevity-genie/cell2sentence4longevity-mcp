# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the vLLM project

import json
from pathlib import Path
from typing import Any

import typer
from openai import OpenAI

# Modify OpenAI's API key and API base to use vLLM's API server.
openai_api_key = "EMPTY"
openai_api_base = "http://89.169.110.141:8000/v1/"


def load_payload(payload_file: Path) -> dict[str, Any]:
    """Load the payload from a JSON file."""
    with open(payload_file) as f:
        return json.load(f)


def main(
    payload: Path = typer.Option(
        Path("vllm_payload.json"),
        help="Path to the JSON payload file",
    ),
    stream: bool = typer.Option(
        False,
        help="Enable streaming response",
    ),
) -> None:
    """Client for vLLM API server."""
    client = OpenAI(
        api_key=openai_api_key,
        base_url=openai_api_base,
    )

    # Load payload from JSON file
    payload_data = load_payload(payload)

    models = client.models.list()
    model = models.data[0].id

    # Override model with the one from payload if needed, or use the first available
    payload_model = payload_data.get("model", model)

    # Prepare completion parameters from payload
    completion_params: dict[str, Any] = {
        "model": payload_model,
        "prompt": payload_data.get("prompt", ""),
        "stream": stream,
    }

    # Add optional parameters from payload if they exist
    optional_keys = ["max_tokens", "temperature", "top_p", "n", "stop", "echo", "logprobs"]
    for key in optional_keys:
        if key in payload_data:
            completion_params[key] = payload_data[key]

    # Completion API
    completion = client.completions.create(**completion_params)

    print("-" * 50)
    print("Completion results:")
    if stream:
        for c in completion:
            print(c)
    else:
        print(completion)
    print("-" * 50)


if __name__ == "__main__":
    typer.run(main)