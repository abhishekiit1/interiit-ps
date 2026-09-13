# agent/core/state.py
from typing import TypedDict, List, Annotated
import operator

class InvestigationState(TypedDict):
    """
    The shared memory dictionary passed between all LangGraph agents.
    Annotated[List[str], operator.add] ensures that when a specialist adds 
    new evidence, it appends to the list rather than overwriting it.
    """
    
    # The initial incident trigger (e.g., "The checkout service is experiencing 5xx errors")
    incident_description: str
    
    # A running log of what tools have been executed to prevent infinite loops
    investigation_steps: Annotated[List[str], operator.add]
    
    # Plausible explanations the Lead Investigator is currently testing
    hypotheses: Annotated[List[str], operator.add]
    
    # Concrete observations returned by your Python tools
    evidence: Annotated[List[str], operator.add]
    
    # The final RCA string containing the root cause, confidence, and alternative explanations
    final_rca: str
    
    # A routing flag to tell LangGraph which node should execute next
    next_node: str