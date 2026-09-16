import os
import time
from langchain_core.messages import SystemMessage
from langchain_core.prompts import load_prompt
from core.llm_init import llm
from core.state import InvestigationState
from yaml import safe_load
from langchain_core.tools import tool
from kubernetes import client, config

# Load the kubeconfig so the agent has the exact same access your terminal does
config.load_kube_config()
v1 = client.CoreV1Api()

@tool
def get_pod_status(namespace: str = "default", app_label: str = "") -> str:
    """
    Fetches the current status and restart counts of Kubernetes pods.
    Use this tool to investigate if containers are crash-looping or failing to start.
    
    Args:
        namespace: The Kubernetes namespace to query (usually "default").
        app_label: Optional label to filter pods by app (e.g., "checkoutservice"). Use for hierarchical drill-downs.
    """
    try:
        if app_label:
            pods = v1.list_namespaced_pod(namespace=namespace, label_selector=f"app={app_label}")
        else:
            pods = v1.list_namespaced_pod(namespace=namespace)
            
        formatted_output = ""
        
        for pod in pods.items:
            name = pod.metadata.name
            phase = pod.status.phase
            
            # Dig into the container statuses to find the actual restart count
            restarts = 0
            if pod.status.container_statuses:
                restarts = sum(c.restart_count for c in pod.status.container_statuses)
                
            formatted_output += f"Pod: {name} | Phase: {phase} | Restarts: {restarts}\n"
            
        # Wrap in sandboxing tags to prevent prompt injection from pod names
        return f"<untrusted_data>\n{formatted_output}\n</untrusted_data>"
        
    except Exception as e:
        return f"Kubernetes query failed: {str(e)}"


def k8s_tool_function(state: InvestigationState) -> InvestigationState:
    """
    Kubernetes Expert Node.
    Analyzes the incident and decides whether to fetch all pod statuses or drill down into a specific suspect app.
    """
    try:
        prompt_template = load_prompt(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../prompts/Kubernetes_Query.yaml"))
        formatted_prompt = prompt_template.format(
            incident_description=state.get("incident_description", ""),
            suspect_components=state.get("suspect_components", []),
            hypotheses=state.get("hypotheses", []),
            evidence=state.get("evidence", [])
        )
        
        response = llm.invoke([SystemMessage(content=formatted_prompt)])
        yaml_response = safe_load(response.content.replace('```yaml', '').replace('```', ''))
        app_label = yaml_response.get("app_label", "").strip()
        last_error = None

        for attempt in range(1, 4):
            try:
                # Invoke the tool with the app_label parameter
                result = get_pod_status.invoke({"namespace": "default", "app_label": app_label})

                if result.startswith("Kubernetes query failed:"):
                    raise RuntimeError(result)

                # Append the tool's raw result directly to the evidence list
                state["evidence"] = [*state.get("evidence", []), result]
                return state
            except Exception as error:
                last_error = error
        
        raise RuntimeError(f"Kubernetes query failed after 3 attempts: {last_error}")
    except Exception as error:
        raise RuntimeError(f"Kubernetes Tool Error:\nReason: {error}") from error