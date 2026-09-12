from fastapi import FastAPI, Request
import uvicorn

app = FastAPI()

@app.post("/alert")
async def receive_alert(request: Request):
    payload = await request.json()
    print("\n🚨 INCOMING ALERT DETECTED 🚨")
    
    alerts = payload.get("alerts", [])
    for alert in alerts:
        status = alert.get("status")
        pod_name = alert.get("labels", {}).get("pod", "Unknown Pod")
        alert_name = alert.get("labels", {}).get("alertname", "Unknown Alert")
        description = alert.get("annotations", {}).get("description", "No description")
        
        print(f"Status: {status}\nAlert: {alert_name}\nTarget Pod: {pod_name}\nDetails: {description}")
        print("-" * 40)
        
    return {"status": "Alert received"}

if __name__ == "__main__":
    print("Starting Agent Listener on port 8080...")
    uvicorn.run(app, host="0.0.0.0", port=8080)
