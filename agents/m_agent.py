from typing import Dict, Any, Optional
import json
import logging
from .base_agent import BaseAgent
from models import MStageResult
from utils import validate_with_retry, normalize_agent_response
from pydantic import ValidationError

logger = logging.getLogger(__name__)


class MAgent(BaseAgent):
    """M-Agent for metastasis staging analysis."""
    
    def get_system_prompt(self) -> str:
        """Load M-staging system prompt."""
        return self.load_prompt_template("m_staging_prompt.txt")
    
    def analyze(self, report_text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Analyze report for M-stage determination.
        
        Args:
            report_text: Markdown text of the radiology report
            context: Optional context (not used for M-Agent)
            
        Returns:
            Dict containing M-stage result validated against MStageResult schema
        """
        logger.info("M-Agent: Starting metastasis staging analysis")
        
        system_prompt = self.get_system_prompt()
        user_message = f"""Analyze the following PET-CT radiology report and determine the M-stage for distant metastases.

Scan the ENTIRE report including all anatomic regions (thorax, abdomen, bones, brain if mentioned).

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
                
                # Parse JSON response
                result_dict = json.loads(response_text)
                
                # Normalize response before validation
                normalized_dict = normalize_agent_response(result_dict.copy())
                
                # Validate against Pydantic model
                m_stage_result = MStageResult(**normalized_dict)
                
                logger.info(f"M-Agent: Determined stage {m_stage_result.stage}")
                logger.info(f"M-Agent: Found {len(m_stage_result.metastasis_sites)} metastatic sites in {m_stage_result.organ_systems_count} organ systems")
                return m_stage_result.model_dump()
                
            except json.JSONDecodeError as e:
                if attempt < max_retries - 1:
                    logger.warning(f"M-Agent: JSON parse failed (attempt {attempt + 1}/{max_retries}), retrying...")
                    time.sleep(retry_delay * (2 ** attempt))
                    continue
                else:
                    logger.error(f"M-Agent: Failed to parse JSON response after {max_retries} attempts: {e}")
                    raise ValueError(f"Invalid JSON response from M-Agent: {e}")
            except ValidationError as e:
                if attempt < max_retries - 1:
                    logger.warning(f"M-Agent: Validation failed (attempt {attempt + 1}/{max_retries}), retrying LLM call...")
                    logger.debug(f"Validation error: {str(e)[:200]}")
                    if 'result_dict' in locals():
                        logger.debug(f"Failed dict: {json.dumps(result_dict, indent=2)}")
                    time.sleep(retry_delay * (2 ** attempt))
                    continue
                else:
                    logger.error(f"M-Agent: Validation failed after {max_retries} attempts: {e}")
                    if 'result_dict' in locals():
                        logger.error(f"M-Agent: Parsed dict was: {json.dumps(result_dict, indent=2)}")
                    raise ValueError(f"M-Agent validation error: {e}")
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"M-Agent: Error (attempt {attempt + 1}/{max_retries}), retrying...")
                    time.sleep(retry_delay * (2 ** attempt))
                    continue
                else:
                    logger.error(f"M-Agent: Analysis failed after {max_retries} attempts: {e}")
                    if 'result_dict' in locals():
                        logger.error(f"M-Agent: Parsed dict was: {json.dumps(result_dict, indent=2)}")
                    raise
