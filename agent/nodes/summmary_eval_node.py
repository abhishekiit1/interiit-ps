import os
from core.state import InvestigationState
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.prompts import load_prompt
from core.llm_init import llm
from yaml import safe_load

def summary_eval_function(state: InvestigationState) -> InvestigationState:
    """Your task is to evaluate the given hypotheses against the given evidence and confidence
    score. After evaluating, generate the Root Cause Analysis report."""
    
    print(f"\n{'='*50}")
    print(f"  📊 [SummaryEvalNode] ENTER")
    print(f"  📊 Evidence count: {len(state.get('evidence', []))}")
    print(f"  📊 Hypotheses: {state.get('hypotheses', [])}")
    print(f"  📊 Confidence: {state.get('confidence', 0.0)}")
    
    try:
        prompt_template = load_prompt(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../prompts/Summary_Evaluation.yaml"))
        formatted_prompt = prompt_template.format(
            incident_description=state.get("incident_description", ""),
            evidence=state.get("evidence", []),
            hypotheses=state.get("hypotheses", []),
            confidence=state.get("confidence", 0.0),
        )
        response = llm.invoke([HumanMessage(content=formatted_prompt)])
        # Strip markdown fences before parsing YAML to prevent PyYAML crash
        clean_yaml = response.content.replace('```yaml', '').replace('```', '').strip()
        
        print(f"  📊 LLM RCA response:\n{clean_yaml[:400]}")
        
        try:
            yaml_response = safe_load(clean_yaml)
        except Exception as yaml_err:
            print(f"  ⚠️ YAML parse failed: {yaml_err}")
            # If YAML parsing fails, create a minimal RCA from the raw text
            yaml_response = {
                "final_rca": {
                    "summary": clean_yaml[:500],
                    "impact": "See raw summary above",
                    "root_cause": "See raw summary above",
                },
                "confidence": state.get("confidence", 0.0),
                "confidence_level": "Low Confidence",
            }
        state["final_rca"] = yaml_response.get("final_rca", {"summary": "RCA generation produced unparseable output."})
        state["confidence"] = float(yaml_response.get("confidence", state.get("confidence", 0.0)))
        state["confidence_level"] = yaml_response.get("confidence_level", "Unknown")
        
        print(f"  📊 Final RCA summary: {state['final_rca'].get('summary', 'N/A')[:200]}")
        print(f"  📊 Confidence level: {state['confidence_level']}")
        print(f"{'='*50}")
        
        return state
    except Exception as error:
        # Last resort: don't crash, return what we have
        print(f"  ⚠️ Summary eval failed: {error}")
        import traceback
        traceback.print_exc()
        state["final_rca"] = {"summary": f"RCA generation failed: {error}", "evidence_collected": state.get("evidence", [])}
        state["confidence_level"] = "Failed"
        return state