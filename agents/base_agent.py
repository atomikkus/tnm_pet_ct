from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
import logging
from mistralai import Mistral
from config import get_settings

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Abstract base class for all specialized TNM staging agents."""
    
    def __init__(self):
        """Initialize the base agent with Mistral client."""
        self.settings = get_settings()
        self.client = Mistral(api_key=self.settings.mistral_api_key)
        self.model = self.settings.mistral_model
        self.temperature = self.settings.temperature
        self.max_tokens = self.settings.max_tokens
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """Get the system prompt for this agent.
        
        Returns:
            str: System prompt defining agent's role and instructions
        """
        pass
    
    @abstractmethod
    def analyze(self, report_text: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Analyze the report and return structured results.
        
        Args:
            report_text: Markdown text of the radiology report
            context: Optional context from other agents (e.g., tumor laterality for N-Agent)
            
        Returns:
            Dict containing the analysis results
        """
        pass
    
    def call_llm(
        self, 
        system_prompt: str, 
        user_message: str,
        response_format: Optional[Dict[str, Any]] = None
    ) -> str:
        """Call Mistral LLM with retry logic.
        
        Args:
            system_prompt: System prompt for the agent
            user_message: User message containing report text and instructions
            response_format: Optional JSON schema for structured output
            
        Returns:
            str: LLM response text
        """
        # Combine system prompt and user message into single user message
        # This matches the working pattern from md_to_json.py
        combined_prompt = f"{system_prompt}\n\n{user_message}"
        
        messages = [
            {"role": "user", "content": combined_prompt}
        ]
        
        for attempt in range(self.settings.max_retries):
            try:
                response = self.client.chat.complete(
                    model=self.model,
                    messages=messages,  # type: ignore
                    response_format=response_format if response_format else None,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens
                )
                
                response_content = response.choices[0].message.content  # type: ignore
                if response_content:
                    return response_content  # type: ignore
                else:
                    raise ValueError("Empty response from Mistral API")
                
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt == self.settings.max_retries - 1:
                    logger.error(f"All retry attempts failed for {self.__class__.__name__}")
                    raise
                import time
                time.sleep(self.settings.retry_delay * (attempt + 1))
    
    def load_prompt_template(self, filename: str) -> str:
        """Load a prompt template from the prompts directory.
        
        Args:
            filename: Name of the prompt file
            
        Returns:
            str: Prompt template content
        """
        from pathlib import Path
        prompt_path = Path(__file__).parent.parent / "prompts" / filename
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
