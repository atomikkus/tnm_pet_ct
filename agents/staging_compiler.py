from typing import Dict, Any
import json
import logging
from .base_agent import BaseAgent
from models import TNMStaging, TStageResult, NStageResult, MStageResult

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
            tnm_staging = TNMStaging(**result_dict)
            
            logger.info(f"Staging Compiler: Final staging - {tnm_staging.tnm_stage} ({tnm_staging.overall_stage})")
            return tnm_staging.model_dump()
            
        except json.JSONDecodeError as e:
            logger.error(f"Staging Compiler: Failed to parse JSON response: {e}")
            raise ValueError(f"Invalid JSON response from Staging Compiler: {e}")
        except Exception as e:
            logger.error(f"Staging Compiler: Compilation failed: {e}")
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
