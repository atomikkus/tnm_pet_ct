from typing import Dict, Any, Optional
import json
import logging
from .base_agent import BaseAgent
from models import TStageResult
from utils import validate_with_retry, normalize_agent_response
from pydantic import ValidationError

logger = logging.getLogger(__name__)


class TAgent(BaseAgent):
    """T-Agent for tumor staging analysis."""
    
    def get_system_prompt(self) -> str:
        """Load T-staging system prompt."""
        return self.load_prompt_template("t_staging_prompt.txt")
    
    def analyze(self, report_text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Analyze report for T-stage determination.
        
        Args:
            report_text: Markdown text of the radiology report
            context: Optional context (not used for T-Agent)
            
        Returns:
            Dict containing T-stage result validated against TStageResult schema
        """
        logger.info("T-Agent: Starting tumor staging analysis")
        
        system_prompt = self.get_system_prompt()
        user_message = f"""Analyze the following PET-CT radiology report and determine the T-stage for the primary lung tumor.

REPORT TEXT:
{report_text}

Provide your analysis in JSON format as specified in the system prompt."""
        
        import time
        
        max_retries = self.settings.max_retries
        retry_delay = self.settings.retry_delay
        
        for attempt in range(max_retries):
            try:
                # Request JSON response from Mistral
                response_text = self.call_llm(
                    system_prompt=system_prompt,
                    user_message=user_message,
                    response_format={"type": "json_object"}
                )
                
                # Debug: Log raw response
                logger.debug(f"T-Agent raw response (attempt {attempt + 1}): {response_text[:500]}")
                
                # Parse JSON response
                result_dict = json.loads(response_text)
                
                # Debug: Log parsed dict
                logger.debug(f"T-Agent parsed dict keys: {result_dict.keys()}")
                logger.debug(f"T-Agent parsed dict: {json.dumps(result_dict, indent=2)}")
                
                # Normalize response before validation
                normalized_dict = normalize_agent_response(result_dict.copy())
                
                # Validate against Pydantic model
                t_stage_result = TStageResult(**normalized_dict)
                
                logger.info(f"T-Agent: Determined stage {t_stage_result.stage}")
                return t_stage_result.model_dump()
                
            except json.JSONDecodeError as e:
                if attempt < max_retries - 1:
                    logger.warning(f"T-Agent: JSON parse failed (attempt {attempt + 1}/{max_retries}), retrying...")
                    time.sleep(retry_delay * (2 ** attempt))
                    continue
                else:
                    logger.error(f"T-Agent: Failed to parse JSON response after {max_retries} attempts: {e}")
                    logger.error(f"T-Agent: Raw response was: {response_text}")
                    raise ValueError(f"Invalid JSON response from T-Agent: {e}")
            except ValidationError as e:
                if attempt < max_retries - 1:
                    logger.warning(f"T-Agent: Validation failed (attempt {attempt + 1}/{max_retries}), retrying LLM call...")
                    logger.debug(f"Validation error: {str(e)[:200]}")
                    if 'result_dict' in locals():
                        logger.debug(f"Failed dict: {json.dumps(result_dict, indent=2)}")
                    time.sleep(retry_delay * (2 ** attempt))
                    continue
                else:
                    logger.error(f"T-Agent: Validation failed after {max_retries} attempts: {e}")
                    if 'result_dict' in locals():
                        logger.error(f"T-Agent: Parsed dict was: {json.dumps(result_dict, indent=2)}")
                    raise ValueError(f"T-Agent validation error: {e}")
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"T-Agent: Error (attempt {attempt + 1}/{max_retries}), retrying...")
                    time.sleep(retry_delay * (2 ** attempt))
                    continue
                else:
                    logger.error(f"T-Agent: Analysis failed after {max_retries} attempts: {e}")
                    if 'result_dict' in locals():
                        logger.error(f"T-Agent: Parsed dict was: {json.dumps(result_dict, indent=2)}")
                    raise
