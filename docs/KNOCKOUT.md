# Insilico Knockout Tool

## Overview

The insilico knockout tool allows you to test the effect of removing genes from a gene expression "cell sentence" on age prediction. This can help identify which genes have the most impact on predicted biological age.

## How It Works

1. **Original Prediction**: The tool first predicts age using the complete gene sentence
2. **Gene Removal**: It removes the first gene (highest expressed) from the sentence
3. **Knockout Prediction**: It predicts age again with the modified sentence
4. **Delta Calculation**: It calculates the change in predicted age (knockout - original)

## Usage

### Via MCP Server

The `insilico_knockout` tool is available as an MCP tool and can be called through AI agents like Claude:

```python
insilico_knockout(
    gene_sentence="MT-CO1 FTL EEF1A1 HLA-B LST1 S100A4 HLA-C H3-3B ZFP36 AIF1",
    sex="female",
    tissue="blood",
    cell_type="CD14-low, CD16-positive monocyte"
)
```

### Via CLI

#### Direct Gene Sentence

```bash
uv run cell2sentence-cli knockout "MT-CO1 FTL EEF1A1 HLA-B LST1 S100A4" \
  --sex female \
  --tissue blood \
  --format csv
```

Output:
```csv
gene_knocked_out,age_prediction,age_prediction_with_knockout,delta_age
MT-CO1,46.0,46.0,0.0
```

#### From Payload File

```bash
uv run cell2sentence-cli knockout-from-payload data/example/vllm_payload.json
```

Output:
```
Gene knocked out: MT-CO1
Age prediction (original): 46.0
Age prediction (knockout): 46.0
Delta age: 0.0
```

## Output Format

The tool returns:
- **gene_knocked_out**: The gene symbol that was removed
- **age_prediction**: Predicted age with full gene sentence
- **age_prediction_with_knockout**: Predicted age after gene removal
- **delta_age**: Change in age (negative = gene removal made younger, positive = made older)

## Interpretation

- **Delta age ≈ 0**: The removed gene has minimal impact on age prediction
- **Delta age < 0**: Removing the gene predicts younger age (gene associated with aging)
- **Delta age > 0**: Removing the gene predicts older age (gene may be protective)

## Example Results

Using the example payload with 1983 genes from OpenGenes database:
- **Original age**: 46.0 years
- **Knockout gene**: MT-CO1 (mitochondrial cytochrome c oxidase I)
- **Knockout age**: 46.0 years
- **Delta**: 0.0 years

In this case, removing MT-CO1 (the highest expressed gene) had no effect on the age prediction, suggesting the model doesn't heavily weight this particular gene for this cell type.

## Use Cases

1. **Gene Prioritization**: Identify which highly expressed genes most impact age predictions
2. **Pathway Analysis**: Test groups of genes from specific pathways
3. **Drug Target Discovery**: Find genes that, when inhibited, could reduce biological age
4. **Quality Control**: Verify that removing irrelevant genes doesn't change predictions
5. **Batch Processing**: Systematically test all genes in a sentence

## Extending the Tool

### Multiple Gene Knockout

To test multiple genes, you can chain knockouts:

```bash
# Remove first gene
uv run cell2sentence-cli knockout "GENE1 GENE2 GENE3 GENE4" --format json

# Then use the knockout_gene_sentence from the output for the next iteration
uv run cell2sentence-cli knockout "GENE2 GENE3 GENE4" --format json
```

### Batch Processing

For systematic analysis of all genes:

```python
from cell2sentence4longevity_mcp.knockout import insilico_knockout

genes = "MT-CO1 FTL EEF1A1 HLA-B LST1 S100A4".split()
results = []

for i in range(len(genes)):
    # Test removing gene at position i
    test_sentence = " ".join(genes[i+1:])  # Remove first i+1 genes
    if test_sentence:
        result = insilico_knockout(
            gene_sentence=" ".join(genes),
            vllm_base_url="http://89.169.110.141:8000",
            model="transhumanist-already-exists/C2S-Scale-Gemma-2-27B-age-prediction-fullft"
        )
        results.append(result)
```

## Technical Details

- Uses eliot for structured logging
- Supports multiple output formats (text, JSON, CSV)
- Logs stored in `logs/knockout.json` and `logs/knockout.log`
- Temperature set to 0.0 for reproducible results
- Uses vLLM completions API with HTTP requests

## References

- Model: `transhumanist-already-exists/C2S-Scale-Gemma-2-27B-age-prediction-fullft`
- Gene Database: OpenGenes (aging-related genes)
- Framework: FastMCP (Model Context Protocol)

