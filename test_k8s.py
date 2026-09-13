from kubernetes import client, config

# 1. Load the same ~/.kube/config file that your terminal uses
config.load_kube_config()

# 2. Create an API client to talk to the core Kubernetes systems
v1 = client.CoreV1Api()

print("🔌 Connecting to Kubernetes API...\n")

# 3. Fetch all pods in the default namespace
print("📦 Current Pods in 'default' namespace:")
pods = v1.list_namespaced_pod(namespace="default")

for pod in pods.items:
    # Extract the name and the current running phase
    name = pod.metadata.name
    phase = pod.status.phase
    print(f"- {name}: {phase}")