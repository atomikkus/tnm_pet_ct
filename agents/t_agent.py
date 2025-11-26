from typing import Dict, Any, Optional
import json
import logging
from .base_agent import BaseAgent
from models import TStageResult

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
        
        try:
            # Request JSON response from Mistral
            response_text = self.call_llm(
                system_prompt=system_prompt,
                user_message=user_message,
                response_format={"type": "json_object"}
            )
            
            # Debug: Log raw response
            logger.debug(f"T-Agent raw response: {response_text[:500]}")
            
            # Parse JSON response
            result_dict = json.loads(response_text)
            
            # Debug: Log parsed dict
            logger.debug(f"T-Agent parsed dict keys: {result_dict.keys()}")
            logger.debug(f"T-Agent parsed dict: {json.dumps(result_dict, indent=2)}")
            
            # Validate against Pydantic model
            t_stage_result = TStageResult(**result_dict)
            
            logger.info(f"T-Agent: Determined stage {t_stage_result.stage}")
            return t_stage_result.model_dump()
            
        except json.JSONDecodeError as e:
            logger.error(f"T-Agent: Failed to parse JSON response: {e}")
            logger.error(f"T-Agent: Raw response was: {response_text}")
            raise ValueError(f"Invalid JSON response from T-Agent: {e}")
        except Exception as e:
            logger.error(f"T-Agent: Analysis failed: {e}")
            if 'result_dict' in locals():
                logger.error(f"T-Agent: Parsed dict was: {json.dumps(result_dict, indent=2)}")
            raise
