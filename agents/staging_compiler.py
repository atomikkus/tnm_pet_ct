from typing import Dict, Any
import json
import logging
from .base_agent import BaseAgent
from models import TNMStaging, TStageResult, NStageResult, MStageResult
from utils import validate_with_retry, normalize_agent_response
from pydantic import ValidationError

logger = logging.getLogger(__name__)


class StagingCompiler(BaseAgent):
    """Staging Compiler agent for combining T, N, M results into final staging."""
    
    def get_system_prompt(self) -> str:
        """Load staging compiler system prompt."""
        return self.load_prompt_template("compiler_prompt.txt")
    
    def compile_staging(
        self,
        t_result: Dict[str, Any],
        n_result: Dict[str, Any],
        m_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Compile final TNM staging from individual component results.
        
        Args:
            t_result: T-stage result dictionary
            n_result: N-stage result dictionary
            m_result: M-stage result dictionary
            
        Returns:
            Dict containing final TNM staging validated against TNMStaging schema
        """
        logger.info("Staging Compiler: Compiling final TNM staging")
        
        system_prompt = self.get_system_prompt()
        
        # Format the input for the compiler
        input_data = {
            "t_stage": t_result,
            "n_stage": n_result,
            "m_stage": m_result
        }
        
        user_message = f"""Compile the final TNM staging from the following individual component analyses:

T-STAGE ANALYSIS:
{json.dumps(t_result, indent=2)}

N-STAGE ANALYSIS:
{json.dumps(n_result, indent=2)}

M-STAGE ANALYSIS:
{json.dumps(m_result, indent=2)}

Tasks:
1. Validate the consistency of these staging components
2. Construct the combined TNM stage string (e.g., T2aN2bM0)
3. Map to the overall prognostic stage group using TNM 9th Edition tables
4. Generate a comprehensive clinical summary

Provide your complete staging result in JSON format as specified in the system prompt."""
        
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
                tnm_staging = TNMStaging(**normalized_dict)
                
                logger.info(f"Staging Compiler: Final staging - {tnm_staging.tnm_stage} ({tnm_staging.overall_stage})")
                return tnm_staging.model_dump()
                
            except json.JSONDecodeError as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Staging Compiler: JSON parse failed (attempt {attempt + 1}/{max_retries}), retrying...")
                    time.sleep(retry_delay * (2 ** attempt))
                    continue
                else:
                    logger.error(f"Staging Compiler: Failed to parse JSON response after {max_retries} attempts: {e}")
                    raise ValueError(f"Invalid JSON response from Staging Compiler: {e}")
            except ValidationError as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Staging Compiler: Validation failed (attempt {attempt + 1}/{max_retries}), retrying LLM call...")
                    logger.debug(f"Validation error: {str(e)[:200]}")
                    if 'result_dict' in locals():
                        logger.debug(f"Failed dict: {json.dumps(result_dict, indent=2)}")
                    time.sleep(retry_delay * (2 ** attempt))
                    continue
                else:
                    logger.error(f"Staging Compiler: Validation failed after {max_retries} attempts: {e}")
                    if 'result_dict' in locals():
                        logger.error(f"Staging Compiler: Parsed dict was: {json.dumps(result_dict, indent=2)}")
                    raise ValueError(f"Staging Compiler validation error: {e}")
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Staging Compiler: Error (attempt {attempt + 1}/{max_retries}), retrying...")
                    time.sleep(retry_delay * (2 ** attempt))
                    continue
                else:
                    logger.error(f"Staging Compiler: Compilation failed after {max_retries} attempts: {e}")
                    if 'result_dict' in locals():
                        logger.error(f"Staging Compiler: Parsed dict was: {json.dumps(result_dict, indent=2)}")
                    raise
    
    def analyze(self, report_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Wrapper method to match BaseAgent interface.
        
        Args:
            report_text: Not used by compiler (kept for interface compatibility)
            context: Must contain 't_result', 'n_result', 'm_result'
            
        Returns:
            Final TNM staging result
        """
        if not all(k in context for k in ['t_result', 'n_result', 'm_result']):
            raise ValueError("Staging Compiler requires t_result, n_result, and m_result in context")
        
        return self.compile_staging(
            t_result=context['t_result'],
            n_result=context['n_result'],
            m_result=context['m_result']
        )
