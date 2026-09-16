from fastapi import FastAPI, Request, BackgroundTasks
import uvicorn
from dotenv import load_dotenv

# Load environment variables (like GOOGLE_API_KEY)
load_dotenv()

# Import the compiled LangGraph agent and state
from graph import agent_graph
from state import InvestigationState

app = FastAPI()

import threading

# Lock to prevent concurrent RCA agents from exhausting the LLM quota
rca_lock = threading.Lock()

def run_investigation(incident_description: str):
    """
    Background task to run the LangGraph agent without blocking the FastAPI response.
    """
    # Prevent concurrent agents to save LLM rate limits
    if not rca_lock.acquire(blocking=False):
        print(f"\n⚠️ RCA Agent already running! Skipping alert to protect API quota: {incident_description[:50]}...")
        return
        

    print("\n" + "="*50)
    print("🤖 SPAWNING LANGGRAPH RCA AGENT 🤖")
    print("="*50)
    
    initial_state = InvestigationState(
    incident_description=incident_description,
    hypotheses=[],
    evidence=[],
    suspect_components=[],
    next_node=0,
    iteration_count=0
    )
    
    try:
        # Invoke the LangGraph swarm
        final_state = agent_graph.invoke(initial_state)
        
        print("\n" + "="*50)
        print("✅ RCA AGENT COMPLETED ✅")
        print("="*50)
        print("\n--- FINAL EVIDENCE GATHERED ---")
        for ev in final_state.get("evidence", []):
            print(ev)
            print("-" * 20)
            
        print("\n" + "="*50)
        print("🚀 ROOT CAUSE ANALYSIS REPORT 🚀")
        print("="*50)
        import yaml
        print(yaml.dump(final_state.get("final_rca", {}), sort_keys=False))
            
    except Exception as e:
        print(f"\n❌ AGENT EXECUTION FAILED: {str(e)}\n")
    finally:
        rca_lock.release()

@app.post("/alert")
async def receive_alert(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()
    print(payload)
    print("\n🚨 INCOMING ALERT DETECTED 🚨")
    
    alerts = payload.get("alerts", [])
    for alert in alerts:
        status = alert.get("status")
        # Only trigger on firing alerts, ignore resolved ones to avoid double execution
        if status == "resolved":
            print("Alert resolved, ignoring.")
            continue
            
        pod_name = alert.get("labels", {}).get("pod", "Unknown Pod")
        alert_name = alert.get("labels", {}).get("alertname", "Unknown Alert")
        description = alert.get("annotations", {}).get("description", "No description")
        
        print(f"Status: {status}\nAlert: {alert_name}\nTarget Pod: {pod_name}\nDetails: {description}")
        print("-" * 40)
        
        # Formulate the incident description from the alert data
        incident_desc = f"Alert Triggered: {alert_name}. Target: {pod_name}. Description: {description}"
        
        # Dispatch the agent execution to the background
        background_tasks.add_task(run_investigation, incident_desc)
        
    return {"status": "Alert received, agent dispatched"}

if __name__ == "__main__":
    print("Starting Agent Listener on port 8080...")
    uvicorn.run(app, host="0.0.0.0", port=3000)
