#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

echo "==============================================="
echo "🚀 Starting Full Cluster Deployment 🚀"
echo "==============================================="

# Optional: Uncomment the line below if you want this script to also create a fresh Kind cluster
# kind create cluster

echo "-----------------------------------------------"
echo "📦 1. Deploying Online Boutique Microservices..."
echo "-----------------------------------------------"
kubectl apply -f ./release/kubernetes-manifests.yaml

echo "-----------------------------------------------"
echo "🔥 2. Adding Helm Repositories..."
echo "-----------------------------------------------"
helm repo add grafana https://grafana.github.io/helm-charts
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

echo "-----------------------------------------------"
echo "🪵  3. Deploying Loki..."
echo "-----------------------------------------------"
helm install loki grafana/loki-stack --namespace default || echo "Loki already exists, skipping..."

echo "-----------------------------------------------"
echo "📈 4. Deploying Prometheus..."
echo "-----------------------------------------------"
helm install prometheus prometheus-community/prometheus \
  --namespace default \
  -f prometheus-values.yaml || echo "Prometheus already exists, skipping..."

echo "==============================================="
echo "✅ All components have been deployed! ✅"
echo "==============================================="
echo ""
echo "Wait a few minutes for the pods to transition from 'ContainerCreating' to 'Running'."
echo "You can check the status at any time by running:"
echo "kubectl get pods"
echo ""
echo "To port-forward the services locally, run:"
echo "kubectl port-forward svc/loki 3100:3100"
echo "kubectl port-forward svc/prometheus-server 9090:80"
