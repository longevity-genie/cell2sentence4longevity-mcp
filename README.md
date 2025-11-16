# cell2sentence4longevity-mcp

MCP (Model Context Protocol) server for age prediction using the Cell2Sentence4Longevity model via vLLM.

## Overview

This MCP server provides an interface to predict biological age from gene expression patterns. It uses the `transhumanist-already-exists/C2S-Scale-Gemma-2-27B-age-prediction-fullft` model hosted on a vLLM endpoint.

The server uses the vLLM completions API directly via HTTP requests, making it easy to integrate age prediction into AI workflows.

## Features

- **Age Prediction**: Predict donor age from gene expression "cell sentences"
- **Metadata Support**: Include additional information like sex, tissue type, cell type, and smoking status
- **Multiple Transport Options**: Supports stdio, SSE, and streamable-http transports
- **Structured Output**: Returns both raw model response and parsed age prediction
- **Example Resources**: Provides example prompts and model information

## Installation

Using `uv`:

```bash
cd /home/antonkulaga/sources/cell2sentence4longevity-mcp
uv sync
```

## Configuration

The server can be configured using environment variables:

- `VLLM_BASE_URL`: The vLLM endpoint URL (default: `http://89.169.110.141:8000`)
- `VLLM_MODEL`: The model name (default: `transhumanist-already-exists/C2S-Scale-Gemma-2-27B-age-prediction-fullft`)
- `MCP_HOST`: Host to bind to (default: `0.0.0.0`)
- `MCP_PORT`: Port to bind to (default: `3002`)

## Usage

### Running the Server

**Stdio mode** (for use with Claude Desktop or other MCP clients):
```bash
uv run cell2sentence4longevity-mcp-stdio
```

**HTTP server mode**:
```bash
uv run cell2sentence4longevity-mcp-run --host 0.0.0.0 --port 3002
```

**SSE mode**:
```bash
uv run cell2sentence4longevity-mcp-sse --host 0.0.0.0 --port 3002
```

### MCP Client Configuration

#### For Claude Desktop (stdio):

Add to your Claude Desktop config:

```json
{
  "mcpServers": {
    "cell2sentence4longevity": {
      "command": "uv",
      "args": [
        "--directory",
        "/home/antonkulaga/sources/cell2sentence4longevity-mcp",
        "run",
        "cell2sentence4longevity-mcp-stdio"
      ],
      "env": {
        "VLLM_BASE_URL": "http://89.169.110.141:8000",
        "VLLM_MODEL": "transhumanist-already-exists/C2S-Scale-Gemma-2-27B-age-prediction-fullft"
      }
    }
  }
}
```

#### For HTTP clients:

```json
{
  "mcpServers": {
    "cell2sentence4longevity": {
      "url": "http://localhost:3002/mcp",
      "transport": "streamable-http"
    }
  }
}
```

## Tools

### predict_age

Predict age from a gene expression sentence.

**Parameters:**
- `gene_sentence` (str): Space-separated list of gene names ordered by descending expression level
- `max_tokens` (int, optional): Maximum tokens to generate (default: 20)
- `temperature` (float, optional): Sampling temperature (default: 0.0)
- `top_p` (float, optional): Nucleus sampling parameter (default: 1.0)

**Example:**
```python
predict_age(
    gene_sentence="MT-CO1 FTL EEF1A1 HLA-B LST1 S100A4 HLA-C H3-3B ZFP36 AIF1 HLA-DRA FCER1G ITGB2 RPS21 ANXA1 RPL3"
)
```

### predict_age_with_metadata

Predict age with additional metadata about the sample.

**Parameters:**
- `gene_sentence` (str): Space-separated list of gene names ordered by descending expression level
- `sex` (str, optional): Sex of the donor (e.g., 'male', 'female')
- `smoking_status` (int, optional): 0 = non-smoker, 1 = smoker
- `tissue` (str, optional): Tissue type (e.g., 'blood', 'brain')
- `cell_type` (str, optional): Cell type (e.g., 'CD14-low, CD16-positive monocyte')
- `max_tokens` (int, optional): Maximum tokens to generate (default: 20)
- `temperature` (float, optional): Sampling temperature (default: 0.0)
- `top_p` (float, optional): Nucleus sampling parameter (default: 1.0)

**Example:**
```python
predict_age_with_metadata(
    gene_sentence="MT-CO1 FTL EEF1A1 HLA-B LST1 S100A4 HLA-C H3-3B ZFP36 AIF1",
    sex="female",
    smoking_status=0,
    tissue="blood",
    cell_type="CD14-low, CD16-positive monocyte"
)
```

## Resources

### resource://cell2sentence/example-prompt

Returns the example prompt from the `vllm_payload.json` file, showing how to format inputs.

### resource://cell2sentence/model-info

Returns information about the model, including endpoint details and capabilities.

## Input Format

The model expects a "cell sentence" - a space-separated list of aging-related gene names ordered by descending expression level. The genes should typically come from aging-related databases like OpenGenes.

Example cell sentence:
```
MT-CO1 FTL EEF1A1 HLA-B LST1 S100A4 HLA-C H3-3B ZFP36 AIF1 HLA-DRA FCER1G ITGB2 RPS21 ANXA1 RPL3 HLA-DRB1 HLA-DRB5 TPM3 RPL22
```

## Cell Sentence Filtering

This repository includes tools to filter cell sentence datasets to include only cells whose sentences start with gene symbols from the OpenGenes database. See [docs/FILTERING.md](docs/FILTERING.md) for detailed documentation.

**Quick start:**

```bash
# CLI version with logging
uv run python filter.py data/example/cells/example_cells.parquet data/output/filtered_cells.parquet

# Interactive notebook version with statistics
uv run python notebook/filter.py
```

The filtering tools:
- Load 2,403 longevity/aging-related genes from OpenGenes
- Filter cells to keep only those where the first gene is in OpenGenes
- Use Polars for memory-efficient processing
- Provide detailed statistics and analysis

## Output Format

The tools return an `AgePredictionResult` containing:
- `predicted_age`: The predicted age in years (float, or None if parsing failed)
- `raw_response`: The raw text response from the model
- `prompt_used`: The complete prompt sent to the model
- `model`: The model name used for prediction

## Development

To add this server to another project or extend it:

```python
from cell2sentence4longevity_mcp import Cell2SentenceMCP

# Create custom server
mcp = Cell2SentenceMCP(
    name="Custom Age Prediction Server",
    vllm_base_url="http://your-vllm-endpoint:8000/",
    model="your-model-name"
)

# Run with your preferred transport
mcp.run(transport="stdio")
```

## License

See LICENSE file for details.

## Authors

- antonkulaga (antonkulaga@gmail.com)
