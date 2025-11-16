#!/usr/bin/env python3
"""Cell2Sentence4Longevity MCP Server - Age prediction interface using vLLM."""

import os
from typing import Dict, Any, Optional, List
from pathlib import Path

import typer
from fastmcp import FastMCP
from pydantic import BaseModel, Field
from eliot import start_action, to_file
import requests

from cell2sentence4longevity_mcp.knockout import insilico_knockout, KnockoutResult

# Configuration
DEFAULT_HOST = os.getenv("MCP_HOST", "0.0.0.0")
DEFAULT_PORT = int(os.getenv("MCP_PORT", "3002"))
DEFAULT_TRANSPORT = os.getenv("MCP_TRANSPORT", "streamable-http")
VLLM_BASE_URL = os.getenv("VLLM_BASE_URL", "http://89.169.110.141:8000")
DEFAULT_MODEL = os.getenv("VLLM_MODEL", "transhumanist-already-exists/C2S-Scale-Gemma-2-27B-age-prediction-fullft")

# Setup logging for MCP server
def setup_mcp_logging() -> None:
    """Setup eliot logging for MCP server to avoid stderr interference."""
    log_dir = Path("logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    
    json_path = log_dir / "mcp_server.json"
    # Only log to file, not stdout/stderr to avoid interfering with MCP protocol
    to_file(open(str(json_path), "a"))

def get_example_payload_path() -> Optional[Path]:
    """Get the path to the example payload file."""
    project_root = Path(__file__).resolve().parent.parent.parent
    payload_path = project_root / "data" / "example" / "vllm_payload.json"
    if payload_path.exists():
        return payload_path
    return None


class AgePredictionResult(BaseModel):
    """Result from an age prediction."""
    predicted_age: Optional[float] = Field(description="Predicted age in years")
    raw_response: str = Field(description="Raw response from the model")
    prompt_used: str = Field(description="The prompt that was sent to the model")
    model: str = Field(description="The model used for prediction")


class Cell2SentenceMCP(FastMCP):
    """Cell2Sentence4Longevity MCP Server for age prediction using vLLM."""
    
    def __init__(
        self, 
        name: str = "Cell2Sentence4Longevity MCP Server",
        vllm_base_url: str = VLLM_BASE_URL,
        model: str = DEFAULT_MODEL,
        **kwargs
    ):
        """Initialize the Cell2Sentence tools with vLLM connection and FastMCP functionality."""
        super().__init__(name=name, **kwargs)
        
        self.vllm_base_url = vllm_base_url
        self.model = model
        
        # Register our tools and resources
        self._register_tools()
        self._register_resources()
    
    def _register_tools(self):
        """Register Cell2Sentence-specific tools."""
        self.tool(
            name="predict_age",
            description="Predict the age of a cell donor from a gene expression sentence. The gene expression sentence should be a space-separated list of aging-related gene names ordered by descending expression level."
        )(self.predict_age)
        
        self.tool(
            name="predict_age_with_metadata",
            description="Predict the age of a cell donor from a gene expression sentence with additional metadata. Provide the gene expression sentence, sex, tissue, cell type, and other relevant metadata."
        )(self.predict_age_with_metadata)
        
        self.tool(
            name="insilico_knockout",
            description="Perform an insilico knockout experiment by removing a specific gene from the gene expression sentence and comparing age predictions. Provide the gene symbol to knock out and the gene expression sentence. Returns original age, knockout age, delta, and a warning if the gene was not found."
        )(self.insilico_knockout_tool)
    
    def _register_resources(self):
        """Register Cell2Sentence-specific resources."""
        
        @self.resource("resource://cell2sentence/example-prompt")
        def get_example_prompt() -> str:
            """
            Get an example prompt for age prediction.
            
            This resource contains an example of how to format the input for age prediction,
            including the gene expression sentence and metadata.
            
            Returns:
                The example prompt text
            """
            with start_action(action_type="get_example_prompt") as action:
                try:
                    import json
                    payload_path = get_example_payload_path()
                    if payload_path and payload_path.exists():
                        with open(payload_path, 'r') as f:
                            payload = json.load(f)
                            example_prompt = payload.get("prompt", "")
                            action.add_success_fields(file_exists=True, prompt_length=len(example_prompt))
                            return example_prompt
                    else:
                        action.add_error_fields(file_exists=False, error="Example payload file not found")
                        return "Example payload file not found. Please check the data/example/vllm_payload.json file."
                except Exception as e:
                    action.add_error_fields(error=str(e), error_type="file_read_error")
                    return f"Error reading example payload: {e}"
        
        @self.resource("resource://cell2sentence/model-info")
        def get_model_info() -> str:
            """
            Get information about the age prediction model.
            
            Returns:
                Information about the model, including its endpoint and capabilities
            """
            return f"""Cell2Sentence4Longevity Age Prediction Model

Model: {self.model}
vLLM Endpoint: {self.vllm_base_url}

This model predicts the age of a cell donor based on gene expression patterns.
Input: A "cell sentence" - a space-separated list of aging-related gene names ordered by descending expression level
Output: Predicted age in years

The model was fine-tuned on the C2S-Scale-Gemma-2-27B architecture for age prediction from gene expression data.

Metadata that can be provided:
- Sex (male/female)
- Smoking status (0 = non-smoker, 1 = smoker)
- Tissue (e.g., blood, brain, liver)
- Cell type (e.g., CD14-low, CD16-positive monocyte)

The gene names should come from aging-related genes (e.g., from the OpenGenes database) and be ordered by expression level (highest to lowest).
"""
    
    def predict_age(
        self,
        gene_sentence: str,
        max_tokens: int = 20,
        temperature: float = 0.0,
        top_p: float = 1.0
    ) -> AgePredictionResult:
        """
        Predict age from a gene expression sentence.
        
        Args:
            gene_sentence: Space-separated list of gene names ordered by descending expression level
            max_tokens: Maximum number of tokens to generate (default: 20)
            temperature: Sampling temperature (default: 0.0 for deterministic output)
            top_p: Nucleus sampling parameter (default: 1.0)
            
        Returns:
            AgePredictionResult: Contains predicted age and raw response
        """
        with start_action(
            action_type="predict_age",
            gene_count=len(gene_sentence.split()),
            max_tokens=max_tokens,
            temperature=temperature
        ) as action:
            prompt = f"""The following is a list of aging related gene names ordered by descending expression level in a cell.

Aging related cell sentence: {gene_sentence}
Predict the Age of the donor from whom these cells were taken.
Answer only with age value in years:"""
            
            try:
                # Use vLLM completions API directly
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "top_p": top_p,
                    "n": 1,
                    "stop": ["<ctrl100>", "<end_of_turn>", "<eos>"]
                }
                
                # Ensure URL ends with /v1/completions
                url = self.vllm_base_url.rstrip("/") + "/v1/completions"
                response = requests.post(url, json=payload, timeout=60)
                response.raise_for_status()
                
                result_data = response.json()
                raw_response = result_data["choices"][0]["text"].strip()
                action.log(message_type="raw_response", response=raw_response)
                
                # Try to extract age as a number
                predicted_age = None
                try:
                    # Try to parse the response as a number
                    import re
                    numbers = re.findall(r'\d+\.?\d*', raw_response)
                    if numbers:
                        predicted_age = float(numbers[0])
                except Exception as parse_error:
                    action.log(message_type="parse_warning", error=str(parse_error))
                
                result = AgePredictionResult(
                    predicted_age=predicted_age,
                    raw_response=raw_response,
                    prompt_used=prompt,
                    model=self.model
                )
                
                action.add_success_fields(predicted_age=predicted_age, raw_response=raw_response)
                return result
                
            except Exception as e:
                action.log(message_type="prediction_error", error=str(e))
                raise ValueError(f"Error during age prediction: {e}") from e
    
    def predict_age_with_metadata(
        self,
        gene_sentence: str,
        sex: Optional[str] = None,
        smoking_status: Optional[int] = None,
        tissue: Optional[str] = None,
        cell_type: Optional[str] = None,
        max_tokens: int = 20,
        temperature: float = 0.0,
        top_p: float = 1.0
    ) -> AgePredictionResult:
        """
        Predict age from a gene expression sentence with metadata.
        
        Args:
            gene_sentence: Space-separated list of gene names ordered by descending expression level
            sex: Sex of the donor (e.g., 'male', 'female')
            smoking_status: Smoking status (0 = non-smoker, 1 = smoker)
            tissue: Tissue type (e.g., 'blood', 'brain', 'liver')
            cell_type: Cell type (e.g., 'CD14-low, CD16-positive monocyte')
            max_tokens: Maximum number of tokens to generate (default: 20)
            temperature: Sampling temperature (default: 0.0 for deterministic output)
            top_p: Nucleus sampling parameter (default: 1.0)
            
        Returns:
            AgePredictionResult: Contains predicted age and raw response
        """
        with start_action(
            action_type="predict_age_with_metadata",
            gene_count=len(gene_sentence.split()),
            sex=sex,
            tissue=tissue,
            cell_type=cell_type
        ) as action:
            # Build prompt with metadata
            prompt_parts = [
                "The following is a list of aging related gene names ordered by descending expression level in a cell.\n"
            ]
            
            if sex:
                prompt_parts.append(f"Sex: {sex}")
            if smoking_status is not None:
                prompt_parts.append(f"Smoking status: {smoking_status}")
            if tissue:
                prompt_parts.append(f"Tissue: {tissue}")
            if cell_type:
                prompt_parts.append(f"Cell type: {cell_type}")
            
            prompt_parts.append(f"Aging related cell sentence: {gene_sentence}")
            prompt_parts.append("Predict the Age of the donor from whom these cells were taken.")
            prompt_parts.append("Answer only with age value in years:")
            
            prompt = "\n".join(prompt_parts)
            
            try:
                # Use vLLM completions API directly
                payload = {
                    "model": self.model,
                    "prompt": prompt,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "top_p": top_p,
                    "n": 1,
                    "stop": ["<ctrl100>", "<end_of_turn>", "<eos>"]
                }
                
                # Ensure URL ends with /v1/completions
                url = self.vllm_base_url.rstrip("/") + "/v1/completions"
                response = requests.post(url, json=payload, timeout=60)
                response.raise_for_status()
                
                result_data = response.json()
                raw_response = result_data["choices"][0]["text"].strip()
                action.log(message_type="raw_response", response=raw_response)
                
                # Try to extract age as a number
                predicted_age = None
                try:
                    # Try to parse the response as a number
                    import re
                    numbers = re.findall(r'\d+\.?\d*', raw_response)
                    if numbers:
                        predicted_age = float(numbers[0])
                except Exception as parse_error:
                    action.log(message_type="parse_warning", error=str(parse_error))
                
                result = AgePredictionResult(
                    predicted_age=predicted_age,
                    raw_response=raw_response,
                    prompt_used=prompt,
                    model=self.model
                )
                
                action.add_success_fields(predicted_age=predicted_age, raw_response=raw_response)
                return result
                
            except Exception as e:
                action.log(message_type="prediction_error", error=str(e))
                raise ValueError(f"Error during age prediction: {e}") from e
    
    def insilico_knockout_tool(
        self,
        gene_symbol: str,
        gene_sentence: str,
        sex: Optional[str] = None,
        smoking_status: Optional[int] = None,
        tissue: Optional[str] = None,
        cell_type: Optional[str] = None,
        max_tokens: int = 20,
        temperature: float = 0.0,
        top_p: float = 1.0
    ) -> KnockoutResult:
        """
        Perform an insilico knockout experiment by removing a specific gene from the sentence.
        
        This tool:
        1. Predicts age from the original gene sentence
        2. Removes the specified gene symbol from the sentence
        3. Predicts age again with the knockout sentence
        4. Computes the delta
        5. Warns if the gene was not found in the sentence
        
        Args:
            gene_symbol: The gene symbol to knock out (remove from the sentence)
            gene_sentence: Space-separated list of gene names ordered by descending expression level
            sex: Sex of the donor (e.g., 'male', 'female')
            smoking_status: Smoking status (0 = non-smoker, 1 = smoker)
            tissue: Tissue type (e.g., 'blood', 'brain', 'liver')
            cell_type: Cell type (e.g., 'CD14-low, CD16-positive monocyte')
            max_tokens: Maximum number of tokens to generate (default: 20)
            temperature: Sampling temperature (default: 0.0 for deterministic output)
            top_p: Nucleus sampling parameter (default: 1.0)
            
        Returns:
            KnockoutResult: Contains original age, knockout age, delta, gene information, and optional warning
        """
        return insilico_knockout(
            gene_symbol=gene_symbol,
            gene_sentence=gene_sentence,
            vllm_base_url=self.vllm_base_url,
            model=self.model,
            sex=sex,
            smoking_status=smoking_status,
            tissue=tissue,
            cell_type=cell_type,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p
        )


# Setup logging before initializing MCP server
setup_mcp_logging()

# Initialize the Cell2Sentence MCP server (which inherits from FastMCP)
mcp = Cell2SentenceMCP()

# Create typer app
app = typer.Typer(help="Cell2Sentence4Longevity MCP Server - Age prediction interface using vLLM")

@app.command("run")
def cli_app(
    host: str = typer.Option(DEFAULT_HOST, "--host", help="Host to bind to"),
    port: int = typer.Option(DEFAULT_PORT, "--port", help="Port to bind to"),
    transport: str = typer.Option("streamable-http", "--transport", help="Transport type")
) -> None:
    """Run the MCP server with specified transport."""
    mcp.run(transport=transport, host=host, port=port)

@app.command("stdio")
def cli_app_stdio(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output")
) -> None:
    """Run the MCP server with stdio transport."""
    mcp.run(transport="stdio")

@app.command("sse")
def cli_app_sse(
    host: str = typer.Option(DEFAULT_HOST, "--host", help="Host to bind to"),
    port: int = typer.Option(DEFAULT_PORT, "--port", help="Port to bind to")
) -> None:
    """Run the MCP server with SSE transport."""
    mcp.run(transport="sse", host=host, port=port)

# Standalone CLI functions for direct script access
def cli_app_run() -> None:
    """Standalone function for cell2sentence4longevity-mcp-run script."""
    mcp.run(transport="streamable-http", host=DEFAULT_HOST, port=DEFAULT_PORT)

def cli_app_stdio() -> None:
    """Standalone function for cell2sentence4longevity-mcp-stdio script."""
    mcp.run(transport="stdio")

def cli_app_sse() -> None:
    """Standalone function for cell2sentence4longevity-mcp-sse script."""
    mcp.run(transport="sse", host=DEFAULT_HOST, port=DEFAULT_PORT)

if __name__ == "__main__":
    app()

