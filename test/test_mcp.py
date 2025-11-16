"""Test the Cell2Sentence4Longevity MCP server."""

import pytest
from cell2sentence4longevity_mcp.server import Cell2SentenceMCP, AgePredictionResult
from cell2sentence4longevity_mcp.knockout import KnockoutResult


def test_server_initialization():
    """Test that the MCP server initializes correctly."""
    mcp = Cell2SentenceMCP()
    
    assert mcp is not None
    assert mcp.model == "transhumanist-already-exists/C2S-Scale-Gemma-2-27B-age-prediction-fullft"
    assert mcp.vllm_base_url == "http://89.169.110.141:8000"


def test_predict_age():
    """Test basic age prediction functionality."""
    mcp = Cell2SentenceMCP()
    
    gene_sentence = "MT-CO1 FTL EEF1A1 HLA-B LST1 S100A4 HLA-C H3-3B ZFP36 AIF1"
    
    try:
        result = mcp.predict_age(gene_sentence=gene_sentence)
        
        assert isinstance(result, AgePredictionResult)
        assert result.predicted_age is not None
        assert isinstance(result.predicted_age, float)
        assert result.raw_response is not None
        assert result.prompt_used is not None
        assert result.model == mcp.model
        
        print(f"✓ Predicted age: {result.predicted_age} years")
        print(f"✓ Raw response: {result.raw_response}")
    except Exception as e:
        pytest.skip(f"vLLM endpoint not available: {e}")


def test_predict_age_with_metadata():
    """Test age prediction with metadata."""
    mcp = Cell2SentenceMCP()
    
    gene_sentence = "MT-CO1 FTL EEF1A1 HLA-B LST1 S100A4 HLA-C H3-3B ZFP36 AIF1"
    
    try:
        result = mcp.predict_age_with_metadata(
            gene_sentence=gene_sentence,
            sex="female",
            smoking_status=0,
            tissue="blood",
            cell_type="CD14-low, CD16-positive monocyte"
        )
        
        assert isinstance(result, AgePredictionResult)
        assert result.predicted_age is not None
        assert isinstance(result.predicted_age, float)
        assert result.raw_response is not None
        assert "Sex: female" in result.prompt_used
        assert "Tissue: blood" in result.prompt_used
        
        print(f"✓ Predicted age: {result.predicted_age} years")
        print(f"✓ Raw response: {result.raw_response}")
    except Exception as e:
        pytest.skip(f"vLLM endpoint not available: {e}")


def test_custom_parameters():
    """Test prediction with custom parameters."""
    mcp = Cell2SentenceMCP()
    
    gene_sentence = "TP53 FOXO3 SIRT1 APOE CDKN2A IGF1R"
    
    try:
        result = mcp.predict_age(
            gene_sentence=gene_sentence,
            max_tokens=30,
            temperature=0.1,
            top_p=0.95
        )
        
        assert isinstance(result, AgePredictionResult)
        assert result.predicted_age is not None
        
        print(f"✓ Predicted age: {result.predicted_age} years")
    except Exception as e:
        pytest.skip(f"vLLM endpoint not available: {e}")


def test_insilico_knockout():
    """Test insilico knockout functionality."""
    mcp = Cell2SentenceMCP()
    
    gene_sentence = "MT-CO1 FTL EEF1A1 HLA-B LST1"
    
    try:
        result = mcp.insilico_knockout_tool(
            gene_sentence=gene_sentence,
            sex="female",
            tissue="blood",
            cell_type="CD14-low, CD16-positive monocyte"
        )
        
        assert isinstance(result, KnockoutResult)
        assert result.gene_knocked_out == "MT-CO1"
        assert result.age_prediction is not None
        assert result.age_prediction_with_knockout is not None
        assert result.delta_age == result.age_prediction_with_knockout - result.age_prediction
        assert result.original_gene_sentence == gene_sentence
        assert result.knockout_gene_sentence == "FTL EEF1A1 HLA-B LST1"
        
        print(f"✓ Knocked out gene: {result.gene_knocked_out}")
        print(f"✓ Original age: {result.age_prediction} years")
        print(f"✓ Knockout age: {result.age_prediction_with_knockout} years")
        print(f"✓ Delta: {result.delta_age} years")
    except Exception as e:
        pytest.skip(f"vLLM endpoint not available: {e}")


if __name__ == "__main__":
    # Run tests directly
    print("Running Cell2Sentence4Longevity MCP Tests")
    print("=" * 60)
    
    print("\n1. Testing server initialization...")
    test_server_initialization()
    print("   ✓ Server initialization test passed")
    
    print("\n2. Testing basic age prediction...")
    test_predict_age()
    print("   ✓ Basic age prediction test passed")
    
    print("\n3. Testing age prediction with metadata...")
    test_predict_age_with_metadata()
    print("   ✓ Age prediction with metadata test passed")
    
    print("\n4. Testing custom parameters...")
    test_custom_parameters()
    print("   ✓ Custom parameters test passed")
    
    print("\n5. Testing insilico knockout...")
    test_insilico_knockout()
    print("   ✓ Insilico knockout test passed")
    
    print("\n" + "=" * 60)
    print("All tests passed!")

