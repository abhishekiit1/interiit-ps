import sys
import os
from dotenv import load_dotenv

sys.path.append(os.path.join(os.getcwd(), "agent"))
sys.path.append(os.path.join(os.getcwd(), "agent", "core"))
load_dotenv()

from agent.core.graph import agent_graph
from agent.core.state import InvestigationState
import logging

logging.basicConfig(level=logging.DEBUG)

def run():
    print("Starting trace...")
    initial_state = InvestigationState(
        incident_description="Test alert: Pod cartservice-5766c97c79-lbc86 is being heavily CPU throttled.",
        hypotheses=[],
        evidence=[],
        suspect_components=[],
        next_node=0,
        iteration_count=0
    )
    
    try:
        # Stream the graph execution to see exactly which node it reaches
        for output in agent_graph.stream(initial_state):
            for key, value in output.items():
                print(f"Output from node '{key}':")
                print("---")
                if "next_node" in value:
                    print(f"Next Node assigned: {value['next_node']}")
                if "hypotheses" in value:
                    print(f"Hypotheses count: {len(value['hypotheses'])}")
                print("---")
    except Exception as e:
        print(f"Execution Failed with exception: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run()
