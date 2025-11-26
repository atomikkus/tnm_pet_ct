from typing import Dict, Any, Optional
import json
import logging
from .base_agent import BaseAgent
from models import MStageResult

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
        
        try:
            # Request JSON response from Mistral
            response_text = self.call_llm(
                system_prompt=system_prompt,
                user_message=user_message,
                response_format={"type": "json_object"}
            )
            
            # Parse JSON response
            result_dict = json.loads(response_text)
            
            # Validate against Pydantic model
            m_stage_result = MStageResult(**result_dict)
            
            logger.info(f"M-Agent: Determined stage {m_stage_result.stage}")
            logger.info(f"M-Agent: Found {len(m_stage_result.metastasis_sites)} metastatic sites in {m_stage_result.organ_systems_count} organ systems")
            return m_stage_result.model_dump()
            
        except json.JSONDecodeError as e:
            logger.error(f"M-Agent: Failed to parse JSON response: {e}")
            raise ValueError(f"Invalid JSON response from M-Agent: {e}")
        except Exception as e:
            logger.error(f"M-Agent: Analysis failed: {e}")
            raise
