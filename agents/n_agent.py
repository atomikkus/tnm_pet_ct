from typing import Dict, Any, Optional
import json
import logging
from .base_agent import BaseAgent
from models import NStageResult

logger = logging.getLogger(__name__)


class NAgent(BaseAgent):
    """N-Agent for lymph node staging analysis."""
    
    def get_system_prompt(self) -> str:
        """Load N-staging system prompt."""
        return self.load_prompt_template("n_staging_prompt.txt")
    
    def analyze(self, report_text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Analyze report for N-stage determination.
        
        Args:
            report_text: Markdown text of the radiology report
            context: Context from T-Agent containing tumor laterality
            
        Returns:
            Dict containing N-stage result validated against NStageResult schema
        """
        logger.info("N-Agent: Starting lymph node staging analysis")
        
        # Extract tumor laterality from context
        laterality = None
        if context and 'tumor_laterality' in context:
            laterality = context['tumor_laterality']
            logger.info(f"N-Agent: Using tumor laterality: {laterality}")
        else:
            logger.warning("N-Agent: No tumor laterality provided in context, attempting to infer from report")
        
        system_prompt = self.get_system_prompt()
        
        # Build user message with laterality context if available
        if laterality:
            user_message = f"""Analyze the following PET-CT radiology report and determine the N-stage for lymph node involvement.

TUMOR LATERALITY: {laterality.upper()}

This is CRITICAL for determining ipsilateral vs contralateral lymph nodes.

REPORT TEXT:
{report_text}

Provide your analysis in JSON format as specified in the system prompt."""
        else:
            user_message = f"""Analyze the following PET-CT radiology report and determine the N-stage for lymph node involvement.

WARNING: Tumor laterality was not provided. Please attempt to determine it from the report and use it for staging.

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
            n_stage_result = NStageResult(**result_dict)
            
            logger.info(f"N-Agent: Determined stage {n_stage_result.stage}")
            logger.info(f"N-Agent: Found {len(n_stage_result.involved_nodes)} involved node stations")
            return n_stage_result.model_dump()
            
        except json.JSONDecodeError as e:
            logger.error(f"N-Agent: Failed to parse JSON response: {e}")
            raise ValueError(f"Invalid JSON response from N-Agent: {e}")
        except Exception as e:
            logger.error(f"N-Agent: Analysis failed: {e}")
            raise
