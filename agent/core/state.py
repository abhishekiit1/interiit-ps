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
    
    # A running log of what tools have been executed to prevent infinite loops
    investigation_steps: Annotated[Sequence[Union[AIMessage, SystemMessage, ToolMessage]], operator.add]
    
    # Plausible explanations the Lead Investigator is currently testing
    hypotheses: Annotated[Sequence[Union[AIMessage, SystemMessage, ToolMessage]], operator.add]
    
    # Concrete observations returned by your Python tools
    evidence:  Annotated[Sequence[Union[AIMessage, SystemMessage, ToolMessage]], operator.add]
    
    # The final RCA string containing the root cause, confidence, and alternative explanations
    final_rca: str
    
    # A routing flag to tell LangGraph which node should execute next
    next_node: int

    # How confident the agent is about the hypotheses
    confidence: float

    # Human-readable confidence label for the final RCA
    confidence_level: str