# Cell2Sentence4Longevity MCP Server - Summary

## What was created

I've successfully created a Model Context Protocol (MCP) server for the Cell2Sentence4Longevity age prediction model, following the architecture of the opengenes-mcp server as a reference.

## Key Components

### 1. Server Implementation (`src/cell2sentence4longevity_mcp/server.py`)
- **Cell2SentenceMCP class**: Main MCP server that inherits from FastMCP
- **Two prediction tools**:
  - `predict_age`: Simple age prediction from gene expression sentence
  - `predict_age_with_metadata`: Age prediction with additional metadata (sex, tissue, cell type, smoking status)
- **Two resources**:
  - `resource://cell2sentence/example-prompt`: Returns example prompt from vllm_payload.json
  - `resource://cell2sentence/model-info`: Returns information about the model and endpoint
- **Direct vLLM integration**: Uses the vLLM completions API via HTTP requests (not chat completions)
- **Eliot logging**: Structured logging with eliot for debugging and monitoring

### 2. Dependencies (`pyproject.toml`)
- `fastmcp>=2.13.1`: MCP framework
- `requests>=2.32.0`: HTTP client for vLLM API calls
- `eliot>=1.17.5`: Structured logging
- `pycomfort>=0.0.18`: Utilities
- `typer>=0.16.0`: CLI framework
- `pydantic>=2.0.0`: Data validation

### 3. Configuration Files
- **mcp-config-stdio.json**: Configuration for stdio transport (Claude Desktop)
- **mcp-config-server.json**: Configuration for HTTP server transport

### 4. Tests
- **test/test_mcp.py**: Comprehensive unit tests with pytest
  - Server initialization test
  - Basic age prediction test
  - Age prediction with metadata test
  - Custom parameters test

### 5. Documentation
- **README.md**: Comprehensive documentation with:
  - Installation instructions
  - Configuration options
  - Usage examples
  - Tool descriptions
  - Input/output formats

## Key Design Decisions

1. **Direct vLLM API calls instead of litellm**: The vLLM endpoint doesn't support chat templates, so we use the completions API directly via HTTP requests.

2. **URL format**: The server correctly handles the vLLM base URL format (`http://89.169.110.141:8000`) without trailing slashes.

3. **Model name**: Uses the full model name `transhumanist-already-exists/C2S-Scale-Gemma-2-27B-age-prediction-fullft` as served by vLLM.

4. **Prompt format**: Follows the exact format from vllm_payload.json:
   ```
   The following is a list of aging related gene names ordered by descending expression level in a cell.
   
   [Optional metadata: Sex, Smoking status, Tissue, Cell type]
   Aging related cell sentence: [gene names]
   Predict the Age of the donor from whom these cells were taken.
   Answer only with age value in years:
   ```

5. **Response parsing**: Extracts numerical age from the model's response using regex.

## Testing

All tests pass successfully:
- Server initializes correctly
- Age predictions work with both simple and complex scenarios
- The full example from vllm_payload.json (1983 genes) predicts age: 46 years
- Simple gene lists also work (e.g., "TP53 FOXO3 SIRT1 APOE" predicts age: 29 years)

## Usage

### Running the server

**Stdio mode** (for Claude Desktop):
```bash
uv run cell2sentence4longevity-mcp-stdio
```

**HTTP server mode**:
```bash
uv run cell2sentence4longevity-mcp-run --host 0.0.0.0 --port 3002
```

### Example API usage

```python
from cell2sentence4longevity_mcp import Cell2SentenceMCP

mcp = Cell2SentenceMCP()

# Simple prediction
result = mcp.predict_age(
    gene_sentence="MT-CO1 FTL EEF1A1 HLA-B LST1 S100A4"
)

# With metadata
result = mcp.predict_age_with_metadata(
    gene_sentence="MT-CO1 FTL EEF1A1 HLA-B LST1 S100A4",
    sex="female",
    tissue="blood",
    cell_type="CD14-low, CD16-positive monocyte"
)

print(f"Predicted age: {result.predicted_age} years")
```

## Environment Variables

- `VLLM_BASE_URL`: vLLM endpoint (default: `http://89.169.110.141:8000`)
- `VLLM_MODEL`: Model name (default: `transhumanist-already-exists/C2S-Scale-Gemma-2-27B-age-prediction-fullft`)
- `MCP_HOST`: Host to bind to (default: `0.0.0.0`)
- `MCP_PORT`: Port to bind to (default: `3002`)

## Files Created/Modified

- `src/cell2sentence4longevity_mcp/server.py` - Main server implementation
- `src/cell2sentence4longevity_mcp/__init__.py` - Package initialization
- `pyproject.toml` - Project dependencies and metadata
- `pytest.ini` - Pytest configuration
- `mcp-config-stdio.json` - Stdio transport configuration
- `mcp-config-server.json` - HTTP transport configuration
- `README.md` - Comprehensive documentation
- `test/test_mcp.py` - Unit tests

## Next Steps

The MCP server is fully functional and ready to use. You can:
1. Add it to your Claude Desktop configuration using mcp-config-stdio.json
2. Run it as an HTTP server and connect from any MCP client
3. Import and use it programmatically in Python code
4. Extend it with additional tools or resources as needed

