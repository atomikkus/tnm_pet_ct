"""
Utility functions for TNM staging system.
"""

from typing import Any, Dict, List
import logging
from pydantic import ValidationError

logger = logging.getLogger(__name__)


def normalize_evidence_field(data: Dict[str, Any], field_name: str = "evidence") -> Dict[str, Any]:
    """
    Normalize evidence field from list to string if needed.
    
    Sometimes LLMs return evidence as a list instead of a string.
    This function converts it to a string by joining list items.
    
    Args:
        data: Dictionary containing the field to normalize
        field_name: Name of the field to normalize (default: "evidence")
        
    Returns:
        Dictionary with normalized field
    """
    if field_name in data:
        value = data[field_name]
        if isinstance(value, list):
            # Join list items with newlines and spaces
            normalized = " ".join(str(item) for item in value if item)
            logger.warning(f"Normalized {field_name} from list to string: {len(value)} items")
            data[field_name] = normalized
        elif value is None:
            # Set empty string if None
            data[field_name] = ""
            logger.warning(f"Normalized {field_name} from None to empty string")
    
    return data


def normalize_agent_response(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize agent response to fix common LLM output issues.
    
    This handles:
    - Evidence fields returned as lists instead of strings
    - None values in required string fields
    
    Args:
        data: Raw agent response dictionary
        
    Returns:
        Normalized dictionary ready for Pydantic validation
    """
    # Normalize evidence field
    data = normalize_evidence_field(data, "evidence")
    
    # Also check nested structures if they have evidence fields
    if "tumor" in data and isinstance(data["tumor"], dict):
        data["tumor"] = normalize_evidence_field(data["tumor"], "evidence")
    if "nodes" in data and isinstance(data["nodes"], dict):
        data["nodes"] = normalize_evidence_field(data["nodes"], "evidence")
    if "metastasis" in data and isinstance(data["metastasis"], dict):
        data["metastasis"] = normalize_evidence_field(data["metastasis"], "evidence")
    
    return data


def validate_with_retry(
    model_class,
    data: Dict[str, Any],
    max_retries: int = 3,
    retry_delay: float = 1.0,
    normalize_fn=None
) -> Any:
    """
    Validate data against a Pydantic model with retry logic and normalization.
    
    Args:
        model_class: Pydantic model class to validate against
        data: Data dictionary to validate
        max_retries: Maximum number of retry attempts
        retry_delay: Base delay between retries (exponential backoff)
        normalize_fn: Optional normalization function to apply before validation
        
    Returns:
        Validated Pydantic model instance
        
    Raises:
        ValidationError: If validation fails after all retries
    """
    import time
    
    last_error = None
    
    for attempt in range(max_retries):
        try:
            # Apply normalization if provided
            normalized_data = normalize_fn(data.copy()) if normalize_fn else data.copy()
            
            # Attempt validation
            return model_class(**normalized_data)
            
        except ValidationError as e:
            last_error = e
            if attempt < max_retries - 1:
                logger.warning(
                    f"Validation attempt {attempt + 1}/{max_retries} failed, retrying... "
                    f"Error: {str(e)[:200]}"
                )
                # Exponential backoff
                time.sleep(retry_delay * (2 ** attempt))
            else:
                logger.error(f"Validation failed after {max_retries} attempts")
        except Exception as e:
            # For non-validation errors, don't retry
            logger.error(f"Unexpected error during validation: {e}")
            raise
    
    # If we get here, all retries failed
    raise last_error

