# agent/core/state.py
from typing import TypedDict, List, Annotated, Sequence, Union
from langchain_core.messages import AIMessage, ToolMessage, SystemMessage
import operator

class InvestigationState(TypedDict):
    """
    The shared memory dictionary passed between all LangGraph agents.
    Annotated[List[str], operator.add] ensures that when a specialist adds 
    new evidence, it appends to the list rather than overwriting it.
    """
    
    # The initial incident trigger (e.g., "The checkout service is experiencing 5xx errors")
    incident_description: str
    
    # The timestamp when the incident was detected, used to anchor time queries in Prometheus and Loki
    incident_timestamp: str

    # High-level isolated suspects (e.g. deployments or services) to drill down into
    suspect_components: list[str]
    
    # A running log of what tools have been executed to prevent infinite loops
    investigation_steps: list[str]
    
    # Plausible explanations the Lead Investigator is currently testing
    hypotheses: list[str]
    
    # Concrete observations returned by your Python tools
    evidence: list[str]
    
    # The final RCA string containing the root cause, confidence, and alternative explanations
    final_rca: str
    
    # A routing flag to tell LangGraph which node should execute next
    next_node: int

    # How confident the agent is about the hypotheses
    confidence: float

    # Human-readable confidence label for the final RCA
    confidence_level: str
    
    # Dedicated counter to prevent infinite loops
    iteration_count: int