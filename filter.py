#!/usr/bin/env python3
"""
Filter cell sentences dataset to include only cells with sentences starting with OpenGenes gene symbols.
"""

import sqlite3
from pathlib import Path
from typing import Set

import polars as pl
from eliot import start_action, to_file
from huggingface_hub import hf_hub_download
from pycomfort.logging import to_nice_file, to_nice_stdout
import typer

app = typer.Typer(help="Filter cell sentences by OpenGenes gene symbols")

# OpenGenes database configuration
HF_REPO_ID = "longevity-genie/bio-mcp-data"
HF_SUBFOLDER = "opengenes"


def get_opengenes_gene_symbols() -> Set[str]:
    """Get all unique gene symbols from OpenGenes database."""
    with start_action(action_type="get_opengenes_gene_symbols") as action:
        try:
            # Download the database from Hugging Face Hub
            db_path = hf_hub_download(
                repo_id=HF_REPO_ID,
                filename="open_genes.sqlite",
                subfolder=HF_SUBFOLDER,
                repo_type="dataset",
                cache_dir=None
            )
            
            # Query for all unique gene symbols
            readonly_uri = f"file:{db_path}?mode=ro"
            with sqlite3.connect(readonly_uri, uri=True) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT DISTINCT HGNC FROM gene_criteria')
                genes = {row[0] for row in cursor.fetchall()}
            
            action.add_success_fields(gene_count=len(genes))
            return genes
        except Exception as e:
            action.add_error_fields(error=str(e), error_type=type(e).__name__)
            raise


def filter_cells_by_gene_symbols(
    input_path: Path,
    output_path: Path,
    gene_symbols: Set[str],
    lazy: bool = True
) -> pl.DataFrame:
    """
    Filter cells to keep only those with sentences starting with OpenGenes gene symbols.
    
    Args:
        input_path: Path to input parquet file or directory
        output_path: Path to output parquet file
        gene_symbols: Set of gene symbols to filter by
        lazy: Use lazy evaluation for memory efficiency
        
    Returns:
        DataFrame with filtered cells
    """
    with start_action(
        action_type="filter_cells_by_gene_symbols",
        input_path=str(input_path),
        output_path=str(output_path),
        gene_count=len(gene_symbols),
        lazy=lazy
    ) as action:
        try:
            # Load the dataset
            if lazy:
                df = pl.scan_parquet(input_path)
            else:
                df = pl.read_parquet(input_path)
            
            original_count = df.select(pl.len()).collect().item() if lazy else len(df)
            action.log(message_type="original_count", count=original_count)
            
            # Filter: extract first gene symbol from cell_sentence and check if it's in OpenGenes
            # cell_sentence format: "GENE1 GENE2 GENE3 ..."
            filtered_df = df.filter(
                pl.col("cell_sentence")
                .str.split(" ")
                .list.first()
                .is_in(list(gene_symbols))
            )
            
            if lazy:
                # Stream to output using sink_parquet for memory efficiency
                filtered_df.sink_parquet(
                    output_path,
                    compression="zstd",
                    compression_level=3
                )
                # Read back to get count
                result_df = pl.scan_parquet(output_path).collect()
            else:
                result_df = filtered_df
                result_df.write_parquet(
                    output_path,
                    compression="zstd",
                    compression_level=3
                )
            
            filtered_count = len(result_df)
            action.add_success_fields(
                original_count=original_count,
                filtered_count=filtered_count,
                filtered_percentage=round(filtered_count / original_count * 100, 2) if original_count > 0 else 0
            )
            
            return result_df
            
        except Exception as e:
            action.add_error_fields(error=str(e), error_type=type(e).__name__)
            raise


@app.command()
def filter_dataset(
    input_path: Path = typer.Argument(
        ...,
        help="Path to input parquet file or directory",
        exists=True
    ),
    output_path: Path = typer.Argument(
        ...,
        help="Path to output parquet file"
    ),
    lazy: bool = typer.Option(
        True,
        "--lazy/--eager",
        help="Use lazy evaluation for memory efficiency"
    ),
    log_dir: Path = typer.Option(
        Path("./logs"),
        "--log-dir",
        help="Directory for log files"
    )
) -> None:
    """
    Filter cell sentences dataset to include only cells with sentences starting with OpenGenes gene symbols.
    """
    # Setup logging
    log_dir.mkdir(parents=True, exist_ok=True)
    json_path = log_dir / "filter.json"
    log_path = log_dir / "filter.log"
    
    to_nice_file(output_file=json_path, rendered_file=log_path)
    to_nice_stdout(output_file=json_path)
    
    with start_action(
        action_type="filter_dataset_main",
        input_path=str(input_path),
        output_path=str(output_path),
        lazy=lazy
    ) as action:
        try:
            # Get OpenGenes gene symbols
            gene_symbols = get_opengenes_gene_symbols()
            typer.echo(f"Loaded {len(gene_symbols)} gene symbols from OpenGenes database")
            
            # Create output directory if needed
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Filter cells
            result_df = filter_cells_by_gene_symbols(
                input_path=input_path,
                output_path=output_path,
                gene_symbols=gene_symbols,
                lazy=lazy
            )
            
            typer.echo(f"Filtered dataset saved to {output_path}")
            typer.echo(f"Filtered cells: {len(result_df)}")
            
            # Display sample
            typer.echo("\nSample of filtered cell sentences:")
            sample = result_df.select("cell_sentence").head(5)
            typer.echo(sample)
            
            action.add_success_fields(success=True)
            
        except Exception as e:
            action.add_error_fields(error=str(e), error_type=type(e).__name__)
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(code=1)


if __name__ == "__main__":
    app()

