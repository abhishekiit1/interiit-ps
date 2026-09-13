# agent/core/tools.py
import requests
from langchain_core.tools import tool


from kubernetes import client, config

import subprocess
import os
from langchain_core.tools import tool

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
        
    except Exception as e:
        return f"Prometheus query failed: {str(e)}"




# Load the kubeconfig so the agent has the exact same access your terminal does
config.load_kube_config()
v1 = client.CoreV1Api()

@tool
def get_pod_status(namespace: str = "default") -> str:
    """
    Fetches the current status and restart counts of all Kubernetes pods.
    Use this tool to investigate if containers are crash-looping or failing to start.
    
    Args:
        namespace: The Kubernetes namespace to query (usually "default").
    """
    try:
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




@tool
def get_recent_git_changes(repo_path: str = ".") -> str:
    """
    Fetches the recent commit history and configuration changes from the local Git repository.
    Use this tool to investigate if a recent deployment, image change, or YAML configuration 
    update caused the current incident.
    
    Args:
        repo_path: The directory path to the git repository (defaults to current directory ".").
    """
    try:
        # Verify it is a valid git repository first
        if not os.path.exists(os.path.join(repo_path, ".git")):
            return "Error: No Git repository found in the specified path."

        # Execute 'git log' to get the last 3 commits and the files they modified
        result = subprocess.run(
            ["git", "log", "-n", "3", "--stat", "--oneline"],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True
        )
        
        git_output = result.stdout.strip()
        if not git_output:
            return "No recent commits found."

        # Wrap in sandboxing tags to prevent prompt injection from commit messages
        return f"<untrusted_data>\n{git_output}\n</untrusted_data>"
        
    except subprocess.CalledProcessError as e:
        return f"Git command failed: {e.stderr}"
    except Exception as e:
        return f"An error occurred while fetching git changes: {str(e)}"


# The Loki port-forward address
LOKI_URL = "http://localhost:3100/loki/api/v1/query_range"

@tool
def query_loki_logs(logql_query: str, limit: int = 50) -> str:
    """
    Executes a LogQL query against the Loki log aggregation server.
    Use this tool to fetch application logs, error messages, or stack traces 
    from specific containers to identify internal code failures or database timeouts.
    
    Args:
        logql_query: A valid LogQL string (e.g., '{app="checkoutservice"} |= "error"').
        limit: Maximum number of log lines to return (default 50 to prevent context overflow).
    """
    try:
        response = requests.get(LOKI_URL, params={'query': logql_query, 'limit': limit})
        response.raise_for_status()
        data = response.json()
        
        results = data.get('data', {}).get('result', [])
        if not results:
            return "No logs found for this query."
            
        formatted_output = ""
        for res in results:
            # Loki returns values as a list of [timestamp, log_line]
            values = res.get('values', [])
            for val in values:
                log_line = val[1].strip()
                formatted_output += f"{log_line}\n"
                
        # Mandatory sandboxing: Treat all application logs as untrusted input
        return f"<untrusted_data>\n{formatted_output.strip()}\n</untrusted_data>"
        
    except Exception as e:
        return f"Loki query failed: {str(e)}"