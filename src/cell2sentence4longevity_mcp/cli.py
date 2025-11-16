#!/usr/bin/env python3
"""CLI for Cell2Sentence4Longevity tools."""

import os
import json
from pathlib import Path
from typing import Optional

import typer
from eliot import start_action
from pycomfort.logging import to_nice_file, to_nice_stdout

from cell2sentence4longevity_mcp.knockout import insilico_knockout, KnockoutResult

# Configuration
DEFAULT_VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", "http://89.169.110.141:8000")
DEFAULT_MODEL = os.getenv("VLLM_MODEL", "transhumanist-already-exists/C2S-Scale-Gemma-2-27B-age-prediction-fullft")

app = typer.Typer(help="Cell2Sentence4Longevity CLI tools")


def setup_logging(log_dir: Optional[Path] = None) -> None:
    """Setup eliot logging to file and stdout."""
    if log_dir is None:
        log_dir = Path("logs")
    
    log_dir.mkdir(parents=True, exist_ok=True)
    
    json_path = log_dir / "knockout.json"
    log_path = log_dir / "knockout.log"
    
    to_nice_file(output_file=str(json_path), rendered_file=str(log_path))
    to_nice_stdout(output_file=str(json_path))


@app.command()
def knockout(
    gene_symbol: str = typer.Argument(..., help="Gene symbol to knock out from the sentence"),
    gene_sentence: str = typer.Argument(..., help="Space-separated list of gene names ordered by descending expression level"),
    sex: Optional[str] = typer.Option(None, "--sex", help="Sex of the donor (e.g., 'male', 'female')"),
    smoking_status: Optional[int] = typer.Option(None, "--smoking-status", help="Smoking status (0 = non-smoker, 1 = smoker)"),
    tissue: Optional[str] = typer.Option(None, "--tissue", help="Tissue type (e.g., 'blood', 'brain', 'liver')"),
    cell_type: Optional[str] = typer.Option(None, "--cell-type", help="Cell type (e.g., 'CD14-low, CD16-positive monocyte')"),
    vllm_base_url: str = typer.Option(DEFAULT_VLLM_BASE_URL, "--vllm-url", help="Base URL for the vLLM API server"),
    model: str = typer.Option(DEFAULT_MODEL, "--model", help="Model name to use for prediction"),
    max_tokens: int = typer.Option(20, "--max-tokens", help="Maximum number of tokens to generate"),
    temperature: float = typer.Option(0.0, "--temperature", help="Sampling temperature"),
    top_p: float = typer.Option(1.0, "--top-p", help="Nucleus sampling parameter"),
    output_format: str = typer.Option("text", "--format", help="Output format: text, json, or csv"),
    log_dir: Optional[Path] = typer.Option(None, "--log-dir", help="Directory for log files"),
) -> None:
    """
    Perform an insilico knockout experiment by removing a specific gene from the sentence.
    
    This command:
    1. Predicts age from the original gene sentence
    2. Removes the specified gene symbol from the sentence
    3. Predicts age again with the knockout sentence
    4. Computes the delta
    5. Warns if the gene was not found in the sentence
    
    Example:
        knockout MT-CO1 "MT-CO1 FTL EEF1A1 HLA-B LST1" --sex female --tissue blood
    """
    setup_logging(log_dir)
    
    with start_action(action_type="cli_knockout", gene_symbol=gene_symbol, format=output_format):
        result = insilico_knockout(
            gene_symbol=gene_symbol,
            gene_sentence=gene_sentence,
            vllm_base_url=vllm_base_url,
            model=model,
            sex=sex,
            smoking_status=smoking_status,
            tissue=tissue,
            cell_type=cell_type,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p
        )
        
        # Output in the requested format
        if output_format == "json":
            typer.echo(result.model_dump_json(indent=2))
        elif output_format == "csv":
            # CSV header
            typer.echo("gene_knocked_out,age_prediction,age_prediction_with_knockout,delta_age,warning")
            # CSV data
            typer.echo(f"{result.gene_knocked_out},{result.age_prediction},{result.age_prediction_with_knockout},{result.delta_age},{result.warning or ''}")
        else:  # text format
            typer.echo(f"Gene knocked out: {result.gene_knocked_out}")
            typer.echo(f"Age prediction (original): {result.age_prediction}")
            typer.echo(f"Age prediction (knockout): {result.age_prediction_with_knockout}")
            typer.echo(f"Delta age: {result.delta_age}")
            if result.warning:
                typer.echo(f"Warning: {result.warning}")


@app.command()
def knockout_from_payload(
    payload_file: Path = typer.Argument(..., help="Path to the JSON payload file"),
    gene_symbol: Optional[str] = typer.Option(None, "--gene-symbol", help="Gene symbol to knock out (defaults to first gene in sentence)"),
    vllm_base_url: str = typer.Option(DEFAULT_VLLM_BASE_URL, "--vllm-url", help="Base URL for the vLLM API server"),
    model: Optional[str] = typer.Option(None, "--model", help="Model name (overrides payload)"),
    output_format: str = typer.Option("text", "--format", help="Output format: text, json, or csv"),
    log_dir: Optional[Path] = typer.Option(None, "--log-dir", help="Directory for log files"),
) -> None:
    """
    Perform an insilico knockout experiment using a payload file.
    
    The payload file should contain:
    - prompt: The full prompt with metadata and gene sentence
    - model: The model to use (optional)
    - max_tokens, temperature, top_p: Generation parameters (optional)
    
    If --gene-symbol is not provided, the first gene in the sentence will be knocked out by default.
    
    Example:
        knockout-from-payload data/example/vllm_payload.json
        knockout-from-payload data/example/vllm_payload.json --gene-symbol FTL
    """
    setup_logging(log_dir)
    
    with start_action(action_type="cli_knockout_from_payload", payload_file=str(payload_file)):
        # Load payload
        with open(payload_file, 'r') as f:
            payload = json.load(f)
        
        # Extract parameters from the prompt
        prompt = payload.get("prompt", "")
        
        # Parse the prompt to extract metadata and gene sentence
        sex = None
        smoking_status = None
        tissue = None
        cell_type = None
        gene_sentence = ""
        
        for line in prompt.split('\n'):
            line = line.strip()
            if line.startswith("Sex:"):
                sex = line.split(":", 1)[1].strip()
            elif line.startswith("Smoking status:"):
                smoking_status = int(line.split(":", 1)[1].strip())
            elif line.startswith("Tissue:"):
                tissue = line.split(":", 1)[1].strip()
            elif line.startswith("Cell type:"):
                cell_type = line.split(":", 1)[1].strip()
            elif line.startswith("Aging related cell sentence:"):
                gene_sentence = line.split(":", 1)[1].strip()
        
        if not gene_sentence:
            raise ValueError("Could not extract gene sentence from payload prompt")
        
        # If gene_symbol is not provided, use the first gene from the sentence
        if gene_symbol is None:
            genes = gene_sentence.split()
            if not genes:
                raise ValueError("Gene sentence is empty")
            gene_symbol = genes[0]
            typer.echo(f"No gene symbol specified, defaulting to first gene: {gene_symbol}")
        
        # Use model from command line or payload
        model_name = model or payload.get("model", DEFAULT_MODEL)
        
        result = insilico_knockout(
            gene_symbol=gene_symbol,
            gene_sentence=gene_sentence,
            vllm_base_url=vllm_base_url,
            model=model_name,
            sex=sex,
            smoking_status=smoking_status,
            tissue=tissue,
            cell_type=cell_type,
            max_tokens=payload.get("max_tokens", 20),
            temperature=payload.get("temperature", 0.0),
            top_p=payload.get("top_p", 1.0)
        )
        
        # Output in the requested format
        if output_format == "json":
            typer.echo(result.model_dump_json(indent=2))
        elif output_format == "csv":
            # CSV header
            typer.echo("gene_knocked_out,age_prediction,age_prediction_with_knockout,delta_age,warning")
            # CSV data
            typer.echo(f"{result.gene_knocked_out},{result.age_prediction},{result.age_prediction_with_knockout},{result.delta_age},{result.warning or ''}")
        else:  # text format
            typer.echo(f"Gene knocked out: {result.gene_knocked_out}")
            typer.echo(f"Age prediction (original): {result.age_prediction}")
            typer.echo(f"Age prediction (knockout): {result.age_prediction_with_knockout}")
            typer.echo(f"Delta age: {result.delta_age}")
            if result.warning:
                typer.echo(f"Warning: {result.warning}")


@app.command(name="ko")
def ko_short(
    gene_symbol: str = typer.Argument(..., help="Gene symbol to knock out"),
    payload_file: Optional[Path] = typer.Option(None, "--payload", "-p", help="Path to payload JSON file (if not provided, reads from data/example/vllm_payload.json)"),
    vllm_base_url: str = typer.Option(DEFAULT_VLLM_BASE_URL, "--vllm-url", help="Base URL for the vLLM API server"),
    model: Optional[str] = typer.Option(None, "--model", help="Model name (overrides payload)"),
    output_format: str = typer.Option("text", "--format", "-f", help="Output format: text, json, or csv"),
    log_dir: Optional[Path] = typer.Option(None, "--log-dir", help="Directory for log files"),
) -> None:
    """
    Short command for in silico knockout experiments.
    
    Example:
        cell2sentence-cli ko KLF6
        cell2sentence-cli ko MT-CO1 -p data/example/vllm_payload.json
        cell2sentence-cli ko FTL --format json
    """
    setup_logging(log_dir)
    
    # Default to example payload if not provided
    if payload_file is None:
        payload_file = Path("data/example/vllm_payload.json")
    
    if not payload_file.exists():
        typer.echo(f"Error: Payload file not found: {payload_file}", err=True)
        raise typer.Exit(code=1)
    
    with start_action(action_type="cli_ko_short", gene_symbol=gene_symbol, payload_file=str(payload_file)):
        # Load payload
        with open(payload_file, 'r') as f:
            payload = json.load(f)
        
        # Extract parameters from the prompt
        prompt = payload.get("prompt", "")
        
        # Parse the prompt to extract metadata and gene sentence
        sex = None
        smoking_status = None
        tissue = None
        cell_type = None
        gene_sentence = ""
        
        for line in prompt.split('\n'):
            line = line.strip()
            if line.startswith("Sex:"):
                sex = line.split(":", 1)[1].strip()
            elif line.startswith("Smoking status:"):
                smoking_status = int(line.split(":", 1)[1].strip())
            elif line.startswith("Tissue:"):
                tissue = line.split(":", 1)[1].strip()
            elif line.startswith("Cell type:"):
                cell_type = line.split(":", 1)[1].strip()
            elif line.startswith("Aging related cell sentence:"):
                gene_sentence = line.split(":", 1)[1].strip()
        
        if not gene_sentence:
            typer.echo("Error: Could not extract gene sentence from payload prompt", err=True)
            raise typer.Exit(code=1)
        
        # Use model from command line or payload
        model_name = model or payload.get("model", DEFAULT_MODEL)
        
        result = insilico_knockout(
            gene_symbol=gene_symbol,
            gene_sentence=gene_sentence,
            vllm_base_url=vllm_base_url,
            model=model_name,
            sex=sex,
            smoking_status=smoking_status,
            tissue=tissue,
            cell_type=cell_type,
            max_tokens=payload.get("max_tokens", 20),
            temperature=payload.get("temperature", 0.0),
            top_p=payload.get("top_p", 1.0)
        )
        
        # Output in the requested format
        if output_format == "json":
            typer.echo(result.model_dump_json(indent=2))
        elif output_format == "csv":
            # CSV header
            typer.echo("gene_knocked_out,age_prediction,age_prediction_with_knockout,delta_age,warning")
            # CSV data
            typer.echo(f"{result.gene_knocked_out},{result.age_prediction},{result.age_prediction_with_knockout},{result.delta_age},{result.warning or ''}")
        else:  # text format
            typer.echo(f"Gene knocked out: {result.gene_knocked_out}")
            typer.echo(f"Age prediction (original): {result.age_prediction}")
            typer.echo(f"Age prediction (knockout): {result.age_prediction_with_knockout}")
            typer.echo(f"Delta age: {result.delta_age}")
            if result.warning:
                typer.echo(f"Warning: {result.warning}")


if __name__ == "__main__":
    app()

