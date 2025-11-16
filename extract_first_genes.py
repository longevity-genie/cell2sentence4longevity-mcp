#!/usr/bin/env python3
"""
Extract first gene symbols from each cell sentence in the dataset.
"""

import polars as pl
from pathlib import Path
from typing import List
import typer

app = typer.Typer(help="Extract first gene symbols from cell sentences")


@app.command()
def extract_first_genes(
    input_path: Path = typer.Argument(
        ...,
        help="Path to input parquet file with cell sentences",
        exists=True
    ),
    output_format: str = typer.Option(
        "print",
        "--output-format",
        "-f",
        help="Output format: 'print' (default), 'json', or 'txt'"
    ),
    output_file: Path = typer.Option(
        None,
        "--output-file",
        "-o",
        help="Path to output file (for json or txt format)"
    )
) -> List[str]:
    """
    Extract the first gene symbol from each cell sentence.
    
    Cell sentences are space-separated lists of gene symbols ordered by descending expression level.
    This function extracts the first (highest expressed) gene from each sentence.
    """
    
    # Read the parquet file
    df = pl.read_parquet(input_path)
    
    # Extract first gene from each cell_sentence
    first_genes = (
        df.select(
            pl.col("cell_sentence")
            .str.split(" ")
            .list.first()
            .alias("first_gene")
        )
        .get_column("first_gene")
        .to_list()
    )
    
    # Remove None values if any
    first_genes = [gene for gene in first_genes if gene is not None]
    
    # Get unique genes and count
    unique_genes = list(set(first_genes))
    unique_genes.sort()
    
    typer.echo(f"\nTotal cell sentences: {len(first_genes)}")
    typer.echo(f"Unique first genes: {len(unique_genes)}")
    
    # Output based on format
    if output_format == "print":
        typer.echo("\nAll unique first gene symbols:")
        for gene in unique_genes:
            typer.echo(gene)
            
    elif output_format == "json":
        import json
        output_data = {
            "total_sentences": len(first_genes),
            "unique_genes_count": len(unique_genes),
            "unique_genes": unique_genes,
            "all_first_genes": first_genes
        }
        
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(output_data, f, indent=2)
            typer.echo(f"\nSaved to {output_file}")
        else:
            typer.echo(json.dumps(output_data, indent=2))
            
    elif output_format == "txt":
        if output_file:
            with open(output_file, 'w') as f:
                f.write('\n'.join(unique_genes))
            typer.echo(f"\nSaved to {output_file}")
        else:
            for gene in unique_genes:
                typer.echo(gene)
    
    return first_genes


if __name__ == "__main__":
    app()

