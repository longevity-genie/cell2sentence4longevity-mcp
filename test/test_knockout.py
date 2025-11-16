#!/usr/bin/env python3
"""Integration test for the insilico knockout tool."""

import sys
from pathlib import Path

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from cell2sentence4longevity_mcp.knockout import insilico_knockout

def test_knockout():
    """Test the insilico knockout function."""
    
    # Simple test with a few genes
    gene_sentence = "MT-CO1 FTL EEF1A1 HLA-B LST1"
    gene_symbol = "MT-CO1"
    
    print(f"Testing knockout of gene '{gene_symbol}' from gene sentence: {gene_sentence}")
    print()
    
    result = insilico_knockout(
        gene_symbol=gene_symbol,
        gene_sentence=gene_sentence,
        vllm_base_url="http://89.169.110.141:8000",
        model="transhumanist-already-exists/C2S-Scale-Gemma-2-27B-age-prediction-fullft",
        sex="female",
        tissue="blood",
        cell_type="CD14-low, CD16-positive monocyte"
    )
    
    print("Results:")
    print(f"  Gene knocked out: {result.gene_knocked_out}")
    print(f"  Original age prediction: {result.age_prediction}")
    print(f"  Knockout age prediction: {result.age_prediction_with_knockout}")
    print(f"  Delta age: {result.delta_age}")
    if result.warning:
        print(f"  Warning: {result.warning}")
    print()
    print(f"  Original sentence: {result.original_gene_sentence}")
    print(f"  Knockout sentence: {result.knockout_gene_sentence}")
    
    # Assertions
    assert result.gene_knocked_out == gene_symbol, f"Knocked out gene should be {gene_symbol}"
    assert result.age_prediction is not None, "Age prediction should not be None"
    assert result.age_prediction_with_knockout is not None, "Knockout age should not be None"
    assert result.delta_age == result.age_prediction_with_knockout - result.age_prediction, "Delta calculation should be correct"
    assert result.warning is None, f"Warning should be None when gene is found, got: {result.warning}"
    assert gene_symbol not in result.knockout_gene_sentence, "Gene should be removed from knockout sentence"
    
    print()
    print("✓ All tests passed!")
    
    # Test with gene not in sentence
    print()
    print("Testing knockout with gene not in sentence...")
    result2 = insilico_knockout(
        gene_symbol="NONEXISTENT",
        gene_sentence=gene_sentence,
        vllm_base_url="http://89.169.110.141:8000",
        model="transhumanist-already-exists/C2S-Scale-Gemma-2-27B-age-prediction-fullft",
        sex="female",
        tissue="blood",
        cell_type="CD14-low, CD16-positive monocyte"
    )
    
    print("Results:")
    print(f"  Gene knocked out: {result2.gene_knocked_out}")
    print(f"  Warning: {result2.warning}")
    assert result2.warning is not None, "Warning should be present when gene is not found"
    assert "not found" in result2.warning, "Warning should mention gene not found"
    print("✓ Warning test passed!")
    
    return result

if __name__ == "__main__":
    test_knockout()

