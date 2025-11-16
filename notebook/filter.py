#!/usr/bin/env python3
"""
Notebook version: Filter cell sentences dataset to include only cells with sentences starting with OpenGenes gene symbols.

This script demonstrates the filtering process step by step and includes visualizations.
"""

import sqlite3
from pathlib import Path
from typing import Set

import polars as pl
from huggingface_hub import hf_hub_download

# Configuration
HF_REPO_ID = "longevity-genie/bio-mcp-data"
HF_SUBFOLDER = "opengenes"

# Paths
DATA_DIR = Path("./data")
INPUT_PATH = DATA_DIR / "example/cells/example_cells.parquet"
OUTPUT_DIR = DATA_DIR / "output"
OUTPUT_PATH = OUTPUT_DIR / "filtered_cells.parquet"

# Create output directory
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 80)
print("Cell Sentences Filtering by OpenGenes Gene Symbols")
print("=" * 80)

# Step 1: Get OpenGenes gene symbols
print("\n[Step 1] Loading gene symbols from OpenGenes database...")

db_path = hf_hub_download(
    repo_id=HF_REPO_ID,
    filename="open_genes.sqlite",
    subfolder=HF_SUBFOLDER,
    repo_type="dataset",
    cache_dir=None
)

readonly_uri = f"file:{db_path}?mode=ro"
with sqlite3.connect(readonly_uri, uri=True) as conn:
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT HGNC FROM gene_criteria')
    gene_symbols = {row[0] for row in cursor.fetchall()}

print(f"✓ Loaded {len(gene_symbols)} unique gene symbols")
print(f"  Sample genes: {list(gene_symbols)[:10]}")

# Step 2: Load the dataset
print("\n[Step 2] Loading cell sentences dataset...")

# Use lazy loading for memory efficiency
df = pl.scan_parquet(INPUT_PATH)
original_count = df.select(pl.len()).collect().item()

print(f"✓ Loaded dataset with {original_count:,} cells")

# Display dataset schema
print("\n  Dataset schema:")
schema_df = pl.DataFrame({
    "column": df.collect_schema().names()[:10],  # First 10 columns
    "type": [str(dtype) for dtype in list(df.collect_schema().dtypes())[:10]]
})
print(schema_df)

# Step 3: Examine cell sentences before filtering
print("\n[Step 3] Examining cell sentences...")

sample_sentences = df.select("cell_sentence").head(5).collect()
print("\n  Sample cell sentences:")
for idx, row in enumerate(sample_sentences.iter_rows(named=True), 1):
    sentence = row["cell_sentence"]
    first_gene = sentence.split()[0] if sentence else "N/A"
    in_opengenes = first_gene in gene_symbols
    print(f"  {idx}. First gene: {first_gene:8s} | In OpenGenes: {in_opengenes}")
    print(f"     Full sentence: {sentence[:80]}...")

# Step 4: Filter the dataset
print("\n[Step 4] Filtering cells by OpenGenes gene symbols...")

# Filter: keep only cells whose sentences start with OpenGenes gene symbols
filtered_df = df.filter(
    pl.col("cell_sentence")
    .str.split(" ")
    .list.first()
    .is_in(list(gene_symbols))
)

# Save filtered dataset with compression
print(f"  Saving filtered dataset to {OUTPUT_PATH}...")
filtered_df.sink_parquet(
    OUTPUT_PATH,
    compression="zstd",
    compression_level=3
)

# Load back for analysis
result_df = pl.read_parquet(OUTPUT_PATH)
filtered_count = len(result_df)

print(f"✓ Filtered dataset saved")
print(f"  Original cells: {original_count:,}")
print(f"  Filtered cells: {filtered_count:,}")
print(f"  Retained: {filtered_count / original_count * 100:.2f}%")

# Step 5: Analyze filtered results
print("\n[Step 5] Analyzing filtered results...")

# Get first gene from each sentence
first_genes_df = result_df.select(
    pl.col("cell_sentence")
    .str.split(" ")
    .list.first()
    .alias("first_gene")
)

# Count occurrences of each gene as first gene
gene_counts = (
    first_genes_df
    .group_by("first_gene")
    .agg(pl.len().alias("count"))
    .sort("count", descending=True)
)

print(f"\n  Top 10 genes appearing first in cell sentences:")
print(gene_counts.head(10))

# Step 6: Display sample of filtered results
print("\n[Step 6] Sample of filtered cell sentences:")

sample_filtered = result_df.select(
    "cell_sentence",
    "cell_type",
    "tissue",
    "age"
).head(5)

for idx, row in enumerate(sample_filtered.iter_rows(named=True), 1):
    print(f"\n  Cell {idx}:")
    print(f"    Type: {row['cell_type']}")
    print(f"    Tissue: {row['tissue']}")
    print(f"    Age: {row['age']}")
    sentence = row['cell_sentence']
    first_gene = sentence.split()[0] if sentence else "N/A"
    print(f"    First gene: {first_gene}")
    print(f"    Sentence: {sentence[:80]}...")

# Step 7: Statistics
print("\n[Step 7] Additional statistics...")

# Count unique first genes
unique_first_genes = first_genes_df.n_unique()
print(f"  Unique genes appearing first: {unique_first_genes}")
print(f"  Coverage of OpenGenes: {unique_first_genes / len(gene_symbols) * 100:.2f}%")

# Cell type distribution
cell_type_dist = (
    result_df
    .group_by("cell_type")
    .agg(pl.len().alias("count"))
    .sort("count", descending=True)
    .head(5)
)
print(f"\n  Top 5 cell types in filtered dataset:")
print(cell_type_dist)

# Tissue distribution
tissue_dist = (
    result_df
    .group_by("tissue")
    .agg(pl.len().alias("count"))
    .sort("count", descending=True)
    .head(5)
)
print(f"\n  Top 5 tissues in filtered dataset:")
print(tissue_dist)

print("\n" + "=" * 80)
print("Filtering complete!")
print(f"Output saved to: {OUTPUT_PATH}")
print("=" * 80)

