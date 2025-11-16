#!/usr/bin/env python3
"""Insilico knockout functionality for gene expression analysis."""

from typing import Optional
from pydantic import BaseModel, Field
from eliot import start_action
import requests


class KnockoutResult(BaseModel):
    """Result from an insilico knockout experiment."""
    gene_knocked_out: str = Field(description="The gene that was knocked out (removed)")
    age_prediction: float = Field(description="Predicted age with full gene sentence")
    age_prediction_with_knockout: float = Field(description="Predicted age after gene knockout")
    delta_age: float = Field(description="Change in predicted age (knockout - original)")
    original_gene_sentence: str = Field(description="Original gene expression sentence")
    knockout_gene_sentence: str = Field(description="Gene expression sentence after knockout")
    model: str = Field(description="The model used for prediction")
    warning: Optional[str] = Field(default=None, description="Warning message if gene was not found or other issues occurred")


def predict_age_from_sentence(
    gene_sentence: str,
    vllm_base_url: str,
    model: str,
    sex: Optional[str] = None,
    smoking_status: Optional[int] = None,
    tissue: Optional[str] = None,
    cell_type: Optional[str] = None,
    max_tokens: int = 20,
    temperature: float = 0.0,
    top_p: float = 1.0,
    gene_to_remove: Optional[str] = None
) -> float:
    """
    Predict age from a gene expression sentence.
    
    Args:
        gene_sentence: Space-separated list of gene names ordered by descending expression level
        vllm_base_url: Base URL for the vLLM API server
        model: Model name to use for prediction
        sex: Sex of the donor (e.g., 'male', 'female')
        smoking_status: Smoking status (0 = non-smoker, 1 = smoker)
        tissue: Tissue type (e.g., 'blood', 'brain', 'liver')
        cell_type: Cell type (e.g., 'CD14-low, CD16-positive monocyte')
        max_tokens: Maximum number of tokens to generate
        temperature: Sampling temperature
        top_p: Nucleus sampling parameter
        gene_to_remove: Gene symbol to remove from the entire prompt (for knockout experiments)
        
    Returns:
        Predicted age as a float
    """
    with start_action(
        action_type="predict_age_from_sentence",
        gene_count=len(gene_sentence.split())
    ) as action:
        # Build prompt with metadata if provided
        prompt_parts = [
            "The following is a list of aging related gene names ordered by descending expression level in a cell.\n"
        ]
        
        if sex:
            prompt_parts.append(f"Sex: {sex}")
        if smoking_status is not None:
            prompt_parts.append(f"Smoking status: {smoking_status}")
        if tissue:
            prompt_parts.append(f"Tissue: {tissue}")
        if cell_type:
            prompt_parts.append(f"Cell type: {cell_type}")
        
        prompt_parts.append(f"Aging related cell sentence: {gene_sentence}")
        prompt_parts.append("Predict the Age of the donor from whom these cells were taken.")
        prompt_parts.append("Answer only with age value in years:")
        
        prompt = "\n".join(prompt_parts)
        
        # Remove the gene symbol from the entire prompt if specified
        if gene_to_remove:
            # Replace gene symbol followed by space, or space followed by gene symbol
            import re
            # Remove gene with surrounding spaces, then clean up multiple spaces
            prompt = prompt.replace(f" {gene_to_remove} ", " ")
            prompt = prompt.replace(f" {gene_to_remove}", "")
            prompt = prompt.replace(f"{gene_to_remove} ", "")
            # Clean up any multiple spaces
            prompt = re.sub(r'\s+', ' ', prompt)
            action.log(message_type="gene_removed_from_prompt", gene=gene_to_remove)
        
        # Use vLLM completions API directly
        payload = {
            "model": model,
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "top_p": top_p,
            "n": 1,
            "stop": ["<ctrl100>", "<end_of_turn>", "<eos>"]
        }
        
        # Ensure URL ends with /v1/completions
        url = vllm_base_url.rstrip("/") + "/v1/completions"
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        
        result_data = response.json()
        raw_response = result_data["choices"][0]["text"].strip()
        action.log(message_type="raw_response", response=raw_response)
        
        # Try to extract age as a number
        import re
        numbers = re.findall(r'\d+\.?\d*', raw_response)
        if not numbers:
            action.log(message_type="parse_error", raw_response=raw_response)
            raise ValueError(f"Could not extract age from response: {raw_response}")
        
        predicted_age = float(numbers[0])
        action.add_success_fields(predicted_age=predicted_age)
        return predicted_age


def insilico_knockout(
    gene_symbol: str,
    gene_sentence: str,
    vllm_base_url: str,
    model: str,
    sex: Optional[str] = None,
    smoking_status: Optional[int] = None,
    tissue: Optional[str] = None,
    cell_type: Optional[str] = None,
    max_tokens: int = 20,
    temperature: float = 0.0,
    top_p: float = 1.0
) -> KnockoutResult:
    """
    Perform an insilico knockout experiment by removing a specific gene from the entire prompt.
    
    This function:
    1. Predicts age from the original gene sentence
    2. Predicts age again with the gene symbol removed from the entire prompt
    3. Computes the delta
    4. Warns if the gene was not found in the sentence
    
    Args:
        gene_symbol: The gene symbol to knock out (remove from the entire prompt)
        gene_sentence: Space-separated list of gene names ordered by descending expression level
        vllm_base_url: Base URL for the vLLM API server
        model: Model name to use for prediction
        sex: Sex of the donor (e.g., 'male', 'female')
        smoking_status: Smoking status (0 = non-smoker, 1 = smoker)
        tissue: Tissue type (e.g., 'blood', 'brain', 'liver')
        cell_type: Cell type (e.g., 'CD14-low, CD16-positive monocyte')
        max_tokens: Maximum number of tokens to generate
        temperature: Sampling temperature
        top_p: Nucleus sampling parameter
        
    Returns:
        KnockoutResult containing original age, knockout age, delta, and optional warning
    """
    with start_action(
        action_type="insilico_knockout",
        gene_symbol=gene_symbol,
        original_gene_count=len(gene_sentence.split())
    ) as action:
        # Split gene sentence into individual genes
        genes = gene_sentence.split()
        
        if not genes:
            raise ValueError("Gene sentence is empty")
        
        # Check if the gene exists in the sentence
        warning_msg = None
        if gene_symbol not in genes:
            warning_msg = f"Warning: Gene '{gene_symbol}' not found in the gene sentence"
            action.log(message_type="gene_not_found", gene=gene_symbol, warning=warning_msg)
        
        # Create knockout sentence by removing the gene
        knockout_genes = [g for g in genes if g != gene_symbol]
        knockout_sentence = " ".join(knockout_genes)
        
        action.log(
            message_type="knockout_gene", 
            gene=gene_symbol,
            found=gene_symbol in genes,
            original_count=len(genes),
            knockout_count=len(knockout_genes)
        )
        
        # Predict age with original sentence (no gene removal)
        age_original = predict_age_from_sentence(
            gene_sentence=gene_sentence,
            vllm_base_url=vllm_base_url,
            model=model,
            sex=sex,
            smoking_status=smoking_status,
            tissue=tissue,
            cell_type=cell_type,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            gene_to_remove=None
        )
        
        # Predict age with gene removed from entire prompt
        age_knockout = predict_age_from_sentence(
            gene_sentence=gene_sentence,  # Keep original sentence
            vllm_base_url=vllm_base_url,
            model=model,
            sex=sex,
            smoking_status=smoking_status,
            tissue=tissue,
            cell_type=cell_type,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            gene_to_remove=gene_symbol  # Remove gene from entire prompt
        )
        
        # Calculate delta
        delta_age = age_knockout - age_original
        
        result = KnockoutResult(
            gene_knocked_out=gene_symbol,
            age_prediction=age_original,
            age_prediction_with_knockout=age_knockout,
            delta_age=delta_age,
            original_gene_sentence=gene_sentence,
            knockout_gene_sentence=knockout_sentence,
            model=model,
            warning=warning_msg
        )
        
        action.add_success_fields(
            gene_knocked_out=gene_symbol,
            gene_found=gene_symbol in genes,
            age_prediction=age_original,
            age_prediction_with_knockout=age_knockout,
            delta_age=delta_age,
            warning=warning_msg
        )
        
        return result

