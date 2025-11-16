# Cell Sentence Filtering by OpenGenes Gene Symbols

This directory contains scripts to filter cell sentence datasets to include only cells whose sentences start with gene symbols from the [OpenGenes database](https://open-genes.com/).

## Overview

The cell sentence dataset contains cells where each cell has a `cell_sentence` field - a space-separated list of gene symbols ordered by expression level. These scripts filter the dataset to keep only cells where the first gene symbol (highest expressed gene) is present in the OpenGenes longevity and aging-related genes database.

## Scripts

### 1. `filter.py` - CLI Tool

A command-line tool with full logging and flexible options.

**Usage:**

```bash
# Basic usage
uv run python filter.py INPUT_PATH OUTPUT_PATH

# With options
uv run python filter.py \
  data/example/cells/example_cells.parquet \
  data/output/filtered_cells.parquet \
  --lazy \
  --log-dir ./logs
```

**Arguments:**
- `INPUT_PATH`: Path to input parquet file or directory
- `OUTPUT_PATH`: Path to output parquet file

**Options:**
- `--lazy/--eager`: Use lazy evaluation for memory efficiency (default: lazy)
- `--log-dir PATH`: Directory for log files (default: ./logs)

**Features:**
- Eliot-based structured logging
- Memory-efficient lazy loading with Polars
- ZSTD compression for output files
- Progress tracking and statistics

### 2. `notebook/filter.py` - Interactive Version

A step-by-step script with detailed output and statistics, ideal for exploration and understanding.

**Usage:**

```bash
uv run python notebook/filter.py
```

**Features:**
- Step-by-step processing with descriptive output
- Statistics and visualizations
- Sample data display at each step
- Gene distribution analysis
- Cell type and tissue distribution

**Output includes:**
- Number of genes loaded from OpenGenes
- Original vs filtered cell counts
- Top genes appearing first in sentences
- Cell type and tissue distributions
- Sample filtered cells

## How It Works

1. **Load OpenGenes Database**: Downloads and queries the OpenGenes SQLite database from HuggingFace Hub to get all unique gene symbols
2. **Load Cell Dataset**: Reads the cell sentences parquet file using Polars (lazy loading for memory efficiency)
3. **Filter**: Keeps only cells where the first gene symbol in the `cell_sentence` starts with an OpenGenes gene symbol
4. **Save**: Writes filtered dataset to parquet with ZSTD compression

## Example Results

From the example dataset (15,084 cells):
- **Filtered cells**: 7,129 (47.26% retention)
- **Unique genes appearing first**: 28
- **Top genes**: FTL (3,254), MT-CO1 (1,235), MT-ATP6 (905), S100A9 (736), S100A8 (542)

## Data Format

### Input Format
The input parquet file should have at least these columns:
- `cell_sentence`: Space-separated gene symbols (e.g., "FTL MT-CO1 RPL10 ...")
- Additional metadata columns (cell_type, tissue, age, etc.) are preserved

### Output Format
The output is a filtered parquet file with:
- Same schema as input
- Only cells where first gene is in OpenGenes
- ZSTD compression (level 3)

## OpenGenes Database

The OpenGenes database contains 2,403 genes related to:
- Longevity and aging
- Lifespan extension experiments
- Age-related changes
- Hallmarks of aging

Data is automatically downloaded from: `longevity-genie/bio-mcp-data` on HuggingFace Hub

## Requirements

- polars
- sqlite3 (built-in)
- eliot
- pycomfort
- huggingface_hub
- typer

All dependencies are managed via `uv` and `pyproject.toml`.

## Performance

- **Memory efficient**: Uses Polars lazy API with streaming
- **Fast**: Polars optimized expressions for filtering
- **Compressed output**: ZSTD compression reduces file size

## Examples

### CLI Example

```bash
# Filter example dataset
uv run python filter.py \
  data/example/cells/example_cells.parquet \
  data/output/filtered_cells.parquet

# Check logs
cat logs/filter.log
```

### Notebook Example

```bash
# Run interactive filtering
uv run python notebook/filter.py

# Output will be saved to data/output/filtered_cells.parquet
```

## Logs

The CLI tool generates structured logs:
- `logs/filter.json`: Machine-readable JSON logs
- `logs/filter.log`: Human-readable rendered logs

Logs include:
- Gene loading statistics
- Filtering progress
- Row counts and percentages
- Error tracking

## Extending

To filter by different criteria:

```python
# Example: Filter by genes that appear in top 5 positions
filtered_df = df.filter(
    pl.col("cell_sentence")
    .str.split(" ")
    .list.slice(0, 5)  # First 5 genes
    .list.eval(pl.element().is_in(list(gene_symbols)))
    .list.any()  # Any of first 5 in OpenGenes
)
```

