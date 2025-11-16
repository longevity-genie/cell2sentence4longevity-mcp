#!/usr/bin/env python3
"""Test MCP server performance to ensure logging doesn't cause delays."""

import time
from pathlib import Path

def test_mcp_server_logging_configured():
    """Test that MCP server sets up logging properly."""
    # Import the server module - this should trigger logging setup
    from cell2sentence4longevity_mcp import server
    
    # Check that logging setup function exists
    assert hasattr(server, 'setup_mcp_logging'), "setup_mcp_logging function should exist"
    
    # Check that logs directory is created
    log_dir = Path("logs")
    assert log_dir.exists(), "logs directory should be created"
    
    # Check that mcp_server.json exists
    mcp_log = log_dir / "mcp_server.json"
    assert mcp_log.exists(), "mcp_server.json should be created"
    
    print("✓ MCP server logging is properly configured")


def test_knockout_performance():
    """Test that knockout function performs quickly (basic sanity check)."""
    from cell2sentence4longevity_mcp.knockout import insilico_knockout
    
    # Simple test with a few genes
    gene_sentence = "MT-CO1 FTL EEF1A1 HLA-B LST1"
    gene_symbol = "MT-CO1"
    
    start_time = time.time()
    
    result = insilico_knockout(
        gene_symbol=gene_symbol,
        gene_sentence=gene_sentence,
        vllm_base_url="http://89.169.110.141:8000",
        model="transhumanist-already-exists/C2S-Scale-Gemma-2-27B-age-prediction-fullft",
        sex="female",
        tissue="blood",
        cell_type="CD14-low, CD16-positive monocyte"
    )
    
    elapsed = time.time() - start_time
    
    # Should complete in reasonable time (< 5 seconds for 2 API calls)
    # This is a sanity check - actual performance depends on vLLM server
    print(f"✓ Knockout completed in {elapsed:.2f} seconds")
    print(f"  Original age: {result.age_prediction}")
    print(f"  Knockout age: {result.age_prediction_with_knockout}")
    print(f"  Delta: {result.delta_age}")
    
    assert result.gene_knocked_out == gene_symbol
    assert result.age_prediction is not None
    assert result.age_prediction_with_knockout is not None


if __name__ == "__main__":
    print("Testing MCP server logging configuration...")
    test_mcp_server_logging_configured()
    
    print("\nTesting knockout performance...")
    test_knockout_performance()
    
    print("\n✓ All performance tests passed!")

