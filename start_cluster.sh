#!/bin/bash
set -e

echo "========================================"
echo "🚀 Starting Automated Cluster Setup..."
echo "========================================"

# 1. Create kind cluster if it doesn't exist
if ! kind get clusters | grep -q "kind"; then
    echo "📦 Creating fresh Kind cluster..."
    kind create cluster
else
    echo "✅ Kind cluster already exists. Continuing..."
fi

# 2. Deploy the microservices demo (Online Boutique)
echo "🛍️ Deploying Online Boutique microservices..."
kubectl apply -f ./release/kubernetes-manifests.yaml

# 3. Add and update Helm Repositories
echo "⚓ Adding Helm repositories for Loki and Prometheus..."
helm repo add grafana https://grafana.github.io/helm-charts || true
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts || true
helm repo update

# 4. Install Loki Stack
echo "🪵 Installing Loki Stack..."
helm upgrade --install loki grafana/loki-stack --namespace default

# 5. Install Prometheus with custom values
echo "📈 Installing Prometheus and Alertmanager..."
helm upgrade --install prometheus prometheus-community/prometheus \
  --namespace default \
  -f prometheus-values.yaml \
  --set pushgateway.enabled=false \
  --set server.persistentVolume.enabled=false

# 6. Wait for critical pods to start before port-forwarding
echo "⏳ Waiting for critical pods to be created..."
sleep 15 # Give the cluster a moment to schedule the pods

echo "Waiting for Prometheus server to be ready..."
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=prometheus,app.kubernetes.io/component=server --timeout=300s --namespace default || true

echo "Waiting for Loki to be ready..."
kubectl wait --for=condition=ready pod -l app=loki --timeout=300s --namespace default || true

# 7. Setup Background Port Forwarding
echo "🔌 Setting up Background Port Forwarding..."

# Clean up any old port-forwards that might be running
pkill -f "kubectl port-forward" || true

# Forward Prometheus
echo "➡️  Forwarding Prometheus to http://localhost:9090..."
kubectl port-forward svc/prometheus-server 9090:80 --namespace default > /dev/null 2>&1 &

# Forward Loki
echo "➡️  Forwarding Loki to http://localhost:3100..."
kubectl port-forward svc/loki 3100:3100 --namespace default > /dev/null 2>&1 &

# Forward Online Boutique Frontend
echo "➡️  Forwarding Frontend to http://localhost:8080..."
kubectl port-forward svc/frontend-external 8080:80 --namespace default > /dev/null 2>&1 &

echo "========================================"
echo "🎉 Cluster setup complete!"
echo "Prometheus: http://localhost:9090"
echo "Loki:       http://localhost:3100"
echo "Frontend:   http://localhost:8080"
echo "========================================"
echo "You can now run your listener: python3 agent/core/listener.py"
