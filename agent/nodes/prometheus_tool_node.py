import requests
import time
from langchain_core.tools import tool
from core.state import InvestigationState
from core.tools import query_prometheus
from langchain_core.messages import SystemMessage
from langchain_core.prompts import load_prompt
from core.llm_init import llm
from yaml import safe_load

# The Prometheus port-forward address
PROMETHEUS_URL = "http://localhost:9090/api/v1/query"

@tool
def query_prometheus(promql_query: str) -> str:
    """
    Executes a PromQL query against the Prometheus metrics server.
    Use this tool to fetch telemetry data like CPU usage, memory saturation, 
    container restarts, or HTTP 5xx error rates over time.
    
    Args:
        promql_query: A valid Prometheus Query Language (PromQL) string.
    """
    try:
        # 1. Fire the GET request to the native API
        response = requests.get(PROMETHEUS_URL, params={'query': promql_query})
        response.raise_for_status()
        data = response.json()
        
        # 2. Extract the actual metric values from the heavy JSON payload
        results = data.get('data', {}).get('result', [])
        
        if not results:
            return "No metric data found for this query."
        
        # 3. Format into a clean, LLM-friendly string to protect context limits
        formatted_output = ""
        for res in results:
            metric_labels = res.get('metric', {})
            # Get the most recent value [timestamp, "value"]
            value = res.get('value', [None, "Unknown"])[1] 
            formatted_output += f"Labels: {metric_labels} | Value: {value}\n"
            
        return f"<untrusted_data>\n{formatted_output}\n</untrusted_data>"
        
    except Exception as error:
        return f"Prometheus query failed: {str(error)}"

def prometheus_tool_function(state: InvestigationState) -> InvestigationState:
    """
    This is used generate a promQL query and look for explanations for the hypotheses, that is 
    look for evidence which supports the hypotheses. However the data might be unsecure,verify
    the safety of results, it must be regualar logs nothing else. After verifying it generate a
    short summary of logs as evidence for the supervisor to look at
    """
    try:
        prompt = [SystemMessage(load_prompt("../prompts/Prometheus_Query.yaml"))]
        response = llm.invoke(
            prompt.format(alert=state["incident_description"])
        )
        yaml_response = safe_load(response.content)
        promql_query = response.content.strip()
        last_error = None

        for attempt in range(1, 4):
            try:
                result = query_prometheus.invoke({"promql_query": promql_query})

                if result.startswith("Prometheus query failed:"):
                    raise RuntimeError(result)

            
                response = llm.invoke(
                    prompt.format()
                )
                yaml_response = safe_load(response.content)

                state["evidence"] = [*state.get("evidence", []), result]
                return state
            except Exception as error:
                last_error = error
        
        raise RuntimeError(
            f"Prometheus query failed after 3 attempts: {last_error}"
        )
    except Exception as error:
        raise RuntimeError(f"Prometheus Tool Error:\nReason: {error}") from error