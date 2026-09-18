# LangGraph Automated RCA Agent

An intelligent, autonomous Root Cause Analysis (RCA) agent powered by LangGraph, Kubernetes, and LLMs (Gemini/OpenRouter). This agent hooks into Prometheus AlertManager to automatically investigate production incidents, query logs and cluster state, and generate detailed root cause analyses.

This repository is built on top of the Google Cloud Online Boutique microservices demo.

---

## 🏗️ Architecture

Our agent operates on a multi-agent swarm architecture using LangGraph, allowing for dynamic, iterative investigation of cluster alerts.

![Architecture Diagram](/images/graph_architecture.png)

### Core Components:
- **Supervisor Node**: The "Brain" of the operation. It receives the initial Prometheus alert, formulates hypotheses, and decides which specialized tool to call next using a bitmask (e.g., `0101` to call both Loki and Prometheus).
- **Tool Proxy Node**: Acts as a router to dispatch the LLM's requests to the correct expert tool nodes.
- **Expert Tool Nodes**: 
  - `PrometheusToolNode`: Queries PromQL for metric anomalies.
  - `LokiToolNode`: Queries LogQL for application logs.
  - `K8sToolNode`: Directly interacts with the Kubernetes API to fetch pod states (e.g., `OOMKilled`, `CrashLoopBackOff`).
  - `GitToolNode`: Checks recent commit history for bad deployments.
- **Summary Eval Node**: The final node that synthesizes all gathered evidence into a comprehensive, human-readable Root Cause Analysis report.

---

## 🚀 Deploy

### 1. Setup Environment Variables
Create a `.env` file in the root directory and add your API keys. We use a multi-provider fallback system:
```env
GOOGLE_API_KEY="your-gemini-key"
OPENROUTER_API_KEY="your-openrouter-key"
OPENROUTER_API_KEY_ALT="your-openrouter-fallback-key"
```

### 2. Clone the Repository
```bash
git clone <link>
cd interiit-ps
```

### 3. Start the Cluster
The startup script provisions a `kind` cluster, installs Loki, Prometheus, and the microservices.
- **For Mac/Windows (Docker Desktop)**:
  ```bash
  ./start_cluster.sh
  ```
- **For Linux**:
  ```bash
  ./start_cluster_linux.sh
  ```

### 4. Start the Agent Listener
Run the FastAPI webhook listener to start accepting alerts from Prometheus:
```bash
source venv/bin/activate
python3 agent/core/listener.py
```

### 5. Inject Chaos
Trigger an alert by injecting chaos into the cluster:
```bash
kubectl apply -f chaos\ injection/cpu-stress.yaml
```

---

## 🛠️ Problems We Faced & How We Fixed Them

Building an autonomous agent that operates in a real Kubernetes environment presented several complex challenges. Here are the top 4 challenges we faced and our engineering solutions:

### 1. Exhaustion of API Quotas & Nested Retry Loops
* **The Problem**: The LangChain SDK's internal retry mechanisms, combined with our custom wrapper's exponential backoff, created massive, invisible delays (hanging for 4+ minutes per request) when free API quotas (Gemini & OpenRouter) were depleted. The agent appeared to get "lost" and would block incoming alerts indefinitely.
* **The Solution**: We engineered a custom "Fail Fast" mechanism. We explicitly disabled internal SDK retries (`max_retries=0`) and reduced our wrapper's sleep cycles. The agent now gracefully falls back through multiple LLM providers or exits cleanly within seconds, releasing the concurrency lock for the next alert.

### 2. Multi-Tool Execution & Graph Routing
* **The Problem**: The LangGraph architecture initially dropped subsequent tool calls because it only processed the highest-order bit of the `next_node` bitmask, preventing the agent from combining tools (e.g., executing Loki + K8s in one turn).
* **The Solution**: We implemented a bitwise clearing algorithm (`bit_to_run = next_node & -next_node`) in the Supervisor routing logic. The graph now sequentially pops and executes tools, routing back to the `ToolProxyNode` until the bitmask is completely cleared (`next_node == 0`).

### 3. Brittle YAML Parsing from LLMs
* **The Problem**: LLMs frequently returned improperly fenced or malformed YAML responses (e.g., returning string scalars instead of dictionaries). This caused `PyYAML` to parse them incorrectly, leading to fatal `'str' object has no attribute 'get'` exceptions across all Tool Nodes.
* **The Solution**: We implemented defensive parsing boundaries and fallbacks (`isinstance(yaml_response, dict)`) across the entire pipeline. If standard parsing fails, the agent intelligently falls back to Regex (`re.search`) to extract critical parameters (like `next_step` and queries) safely.

### 4. Cross-OS Docker Networking (Linux vs Mac)
* **The Problem**: The AlertManager webhook relies on `host.docker.internal` to ping the local Python listener on port 3000. This works natively on Mac, but fails entirely on Linux `kind` clusters.
* **The Solution**: We engineered a dynamic cluster setup script (`start_cluster_linux.sh`) that automatically queries Docker for the `kind` network gateway IP and patches `prometheus-values.yaml` on the fly using `sed`.

---

## 📊 Results

We successfully stress-tested the agent pipeline. We were able to generate 2 RCAs (one successful and one failed due to strict token/credit limits on the LLM APIs). 

When successful, the agent accurately identifies the failing pod (e.g., `cartservice` OOMKilled) and returns a structured YAML RCA report detailing the root cause and confidence level.

![RCA Screenshot](/images/rca_scrnsht.png)

---

## 🚧 Remaining Work

- **Refine and Optimize Tools**: Currently, all tools are not always able to execute optimally due to hitting the rate limits of free-tier APIs. The log and metric payloads can be extremely token-heavy.
- **Token Compression**: We need to implement intelligent summarization within the Python tool nodes (e.g., truncating logs, stripping boilerplate JSON) *before* passing the evidence back to the LLM to stay within the 512/1024 token limits of free keys.
