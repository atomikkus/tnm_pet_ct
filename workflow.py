"""
TNM Staging Workflow Orchestrator

This module orchestrates the multi-agent workflow for TNM staging prediction.
Uses LangGraph for state management and agent coordination.
"""

from typing import TypedDict, Dict, Any, Optional
from langgraph.graph import StateGraph, END
import logging
from agents import TAgent, NAgent, MAgent, StagingCompiler

logger = logging.getLogger(__name__)


class TNMWorkflowState(TypedDict):
    """State for the TNM staging workflow."""
    report_text: str
    report_id: Optional[str]
    patient_id: Optional[str]
    t_result: Optional[Dict[str, Any]]
    n_result: Optional[Dict[str, Any]]
    m_result: Optional[Dict[str, Any]]
    final_staging: Optional[Dict[str, Any]]
    error: Optional[str]


class TNMWorkflow:
    """Orchestrator for TNM staging workflow using LangGraph."""
    
    def __init__(self):
        """Initialize the workflow and agents."""
        self.t_agent = TAgent()
        self.n_agent = NAgent()
        self.m_agent = MAgent()
        self.compiler = StagingCompiler()
        self.graph = self._build_graph()
    
    def _t_agent_node(self, state: TNMWorkflowState) -> TNMWorkflowState:
        """Execute T-Agent analysis."""
        try:
            logger.info("Workflow: Executing T-Agent")
            t_result = self.t_agent.analyze(state["report_text"])
            state["t_result"] = t_result
            return state
        except Exception as e:
            logger.error(f"Workflow: T-Agent failed: {e}")
            state["error"] = f"T-Agent error: {str(e)}"
            return state
    
    def _n_agent_node(self, state: TNMWorkflowState) -> TNMWorkflowState:
        """Execute N-Agent analysis with tumor laterality context."""
        try:
            logger.info("Workflow: Executing N-Agent")
            
            # Extract laterality from T-result if available
            context = {}
            if state.get("t_result"):
                laterality = state["t_result"].get("laterality")
                if laterality:
                    context["tumor_laterality"] = laterality
            
            n_result = self.n_agent.analyze(state["report_text"], context=context)
            state["n_result"] = n_result
            return state
        except Exception as e:
            logger.error(f"Workflow: N-Agent failed: {e}")
            state["error"] = f"N-Agent error: {str(e)}"
            return state
    
    def _m_agent_node(self, state: TNMWorkflowState) -> TNMWorkflowState:
        """Execute M-Agent analysis."""
        try:
            logger.info("Workflow: Executing M-Agent")
            m_result = self.m_agent.analyze(state["report_text"])
            state["m_result"] = m_result
            return state
        except Exception as e:
            logger.error(f"Workflow: M-Agent failed: {e}")
            state["error"] = f"M-Agent error: {str(e)}"
            return state
    
    def _compiler_node(self, state: TNMWorkflowState) -> TNMWorkflowState:
        """Execute Staging Compiler to combine results."""
        try:
            logger.info("Workflow: Executing Staging Compiler")
            
            if not all([state.get("t_result"), state.get("n_result"), state.get("m_result")]):
                raise ValueError("Missing one or more staging components (T/N/M)")
            
            context = {
                "t_result": state["t_result"],
                "n_result": state["n_result"],
                "m_result": state["m_result"]
            }
            
            final_staging = self.compiler.analyze(report_text="", context=context)
            state["final_staging"] = final_staging
            return state
        except Exception as e:
            logger.error(f"Workflow: Staging Compiler failed: {e}")
            state["error"] = f"Staging Compiler error: {str(e)}"
            return state
    
    def _should_continue_after_agents(self, state: TNMWorkflowState) -> str:
        """Determine if workflow should continue to compiler or end due to errors."""
        if state.get("error"):
            logger.error(f"Workflow: Stopping due to error: {state['error']}")
            return END
        
        # Check if all agents completed
        if all([state.get("t_result"), state.get("n_result"), state.get("m_result")]):
            return "compiler"
        else:
            logger.error("Workflow: One or more agents failed to produce results")
            state["error"] = "Incomplete staging results"
            return END
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        workflow = StateGraph(TNMWorkflowState)
        
        # Add nodes
        workflow.add_node("t_agent", self._t_agent_node)
        workflow.add_node("n_agent", self._n_agent_node)
        workflow.add_node("m_agent", self._m_agent_node)
        workflow.add_node("compiler", self._compiler_node)
        
        # Define edges - Sequential execution to avoid state conflicts
        # T-Agent first (provides laterality for N-Agent)
        workflow.set_entry_point("t_agent")
        
        # Then N-Agent (uses laterality from T-Agent)
        workflow.add_edge("t_agent", "n_agent")
        
        # Then M-Agent
        workflow.add_edge("n_agent", "m_agent")
        
        # Finally check if we should continue to compiler
        workflow.add_conditional_edges(
            "m_agent",
            self._should_continue_after_agents,
            {
                "compiler": "compiler",
                END: END
            }
        )
        
        # Compiler is the final node
        workflow.add_edge("compiler", END)
        
        return workflow.compile()
    
    def run(
        self,
        report_text: str,
        report_id: Optional[str] = None,
        patient_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Run the complete TNM staging workflow.
        
        Args:
            report_text: Markdown text from PDF OCR conversion
            report_id: Optional report identifier
            patient_id: Optional patient identifier
            
        Returns:
            Dict containing final TNM staging results or error information
        """
        logger.info("Workflow: Starting TNM staging analysis")
        
        initial_state: TNMWorkflowState = {
            "report_text": report_text,
            "report_id": report_id,
            "patient_id": patient_id,
            "t_result": None,
            "n_result": None,
            "m_result": None,
            "final_staging": None,
            "error": None
        }
        
        try:
            # Execute the workflow
            final_state = self.graph.invoke(initial_state)
            
            if final_state.get("error"):
                logger.error(f"Workflow completed with error: {final_state['error']}")
                return {
                    "success": False,
                    "error": final_state["error"],
                    "partial_results": {
                        "t_result": final_state.get("t_result"),
                        "n_result": final_state.get("n_result"),
                        "m_result": final_state.get("m_result")
                    }
                }
            
            logger.info("Workflow: Successfully completed TNM staging")
            return {
                "success": True,
                "staging": final_state["final_staging"],
                "report_id": report_id,
                "patient_id": patient_id
            }
            
        except Exception as e:
            logger.error(f"Workflow: Unexpected error: {e}")
            return {
                "success": False,
                "error": f"Workflow error: {str(e)}"
            }


def run_tnm_staging_workflow(
    report_text: str,
    report_id: Optional[str] = None,
    patient_id: Optional[str] = None
) -> Dict[str, Any]:
    """Convenience function to run TNM staging workflow.
    
    Args:
        report_text: Markdown text from PDF OCR conversion
        report_id: Optional report identifier
        patient_id: Optional patient identifier
        
    Returns:
        Dict containing final TNM staging results
    """
    workflow = TNMWorkflow()
    return workflow.run(report_text, report_id, patient_id)
