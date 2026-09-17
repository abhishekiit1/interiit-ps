"""
Full pipeline dry-run debugger.
Traces each LangGraph node step-by-step, printing the state transitions
and capturing exactly where / why the pipeline stalls or crashes.
"""
import sys, os, time, traceback
from dotenv import load_dotenv

sys.path.append(os.path.join(os.getcwd(), "agent"))
sys.path.append(os.path.join(os.getcwd(), "agent", "core"))
load_dotenv()

# ── Step 1: Verify LLM works at all ─────────────────────────────────
print("=" * 60)
print("STEP 1: Testing raw LLM connectivity")
print("=" * 60)

from agent.core.llm_init import llm
from langchain_core.messages import HumanMessage

try:
    t0 = time.time()
    resp = llm.invoke([HumanMessage(content="Reply with exactly: OK")])
    elapsed = time.time() - t0
    print(f"  ✅ LLM responded in {elapsed:.1f}s")
    print(f"  Content type: {type(resp.content)}")
    print(f"  Content: {repr(resp.content[:200])}")
except Exception as e:
    print(f"  ❌ LLM FAILED: {e}")
    traceback.print_exc()
    print("\n⛔ Cannot proceed — LLM is broken. Fix llm_init.py first.")
    sys.exit(1)

# ── Step 2: Test prompt loading ──────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 2: Testing all prompt templates load and format correctly")
print("=" * 60)

from langchain_core.prompts import load_prompt

prompts_dir = os.path.join(os.getcwd(), "agent", "prompts")
test_vars = {
    "Investigation_Begin.yaml": {"alert": "Test alert"},
    "Iterative_Investigation.yaml": {
        "incident_description": "test",
        "incident_timestamp": "2026-01-01T00:00:00Z",
        "suspect_components": ["testpod"],
        "hypotheses": ["H1"],
        "evidence": ["E1"],
    },
    "Prometheus_Query.yaml": {
        "incident_description": "test",
        "incident_timestamp": "2026-01-01T00:00:00Z",
        "suspect_components": ["testpod"],
        "hypotheses": ["H1"],
        "evidence": ["E1"],
    },
    "Loki_Query.yaml": {
        "incident_description": "test",
        "incident_timestamp": "2026-01-01T00:00:00Z",
        "suspect_components": ["testpod"],
        "hypotheses": ["H1"],
        "evidence": ["E1"],
    },
    "Kubernetes_Query.yaml": {
        "incident_description": "test",
        "suspect_components": ["testpod"],
        "hypotheses": ["H1"],
        "evidence": ["E1"],
    },
    "Git_status.yaml": {
        "incident_description": "test",
        "suspect_components": ["testpod"],
        "hypotheses": ["H1"],
        "evidence": ["E1"],
    },
    "Summary_Evaluation.yaml": {
        "incident_description": "test",
        "evidence": ["E1"],
        "hypotheses": ["H1"],
        "confidence": 0.5,
    },
}

for fname, variables in test_vars.items():
    path = os.path.join(prompts_dir, fname)
    try:
        tmpl = load_prompt(path)
        formatted = tmpl.format(**variables)
        print(f"  ✅ {fname} — loaded and formatted OK ({len(formatted)} chars)")
    except Exception as e:
        print(f"  ❌ {fname} — FAILED: {e}")
        traceback.print_exc()

# ── Step 3: Test K8s tool ────────────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 3: Testing Kubernetes tool connectivity")
print("=" * 60)

try:
    from agent.nodes.k8s_tool_node import get_pod_status
    result = get_pod_status.invoke({"namespace": "default", "app_label": ""})
    lines = result.strip().split("\n")
    print(f"  ✅ K8s tool returned {len(lines)} lines")
    for line in lines[:5]:
        print(f"     {line}")
except Exception as e:
    print(f"  ❌ K8s tool FAILED: {e}")

# ── Step 4: Test Prometheus connectivity ─────────────────────────────
print("\n" + "=" * 60)
print("STEP 4: Testing Prometheus connectivity")
print("=" * 60)

try:
    from agent.nodes.prometheus_tool_node import query_prometheus
    result = query_prometheus.invoke({"promql_query": "up"})
    lines = result.strip().split("\n")
    print(f"  ✅ Prometheus returned {len(lines)} lines")
    for line in lines[:3]:
        print(f"     {line}")
except Exception as e:
    print(f"  ❌ Prometheus FAILED: {e}")
    print(f"     Is port-forward running? kubectl port-forward svc/prometheus-server 9090:80")

# ── Step 5: Test Loki connectivity ───────────────────────────────────
print("\n" + "=" * 60)
print("STEP 5: Testing Loki connectivity")
print("=" * 60)

try:
    from agent.nodes.loki_tool_node import query_loki_logs
    result = query_loki_logs.invoke({"logql_query": '{job="default/kubernetes"}', "limit": 5})
    print(f"  ✅ Loki returned: {result[:200]}")
except Exception as e:
    print(f"  ❌ Loki FAILED: {e}")
    print(f"     Is port-forward running? kubectl port-forward svc/loki 3100:3100")

# ── Step 6: Full graph dry run ───────────────────────────────────────
print("\n" + "=" * 60)
print("STEP 6: Running FULL LangGraph pipeline (streaming)")
print("=" * 60)

from agent.core.graph import agent_graph
from agent.core.state import InvestigationState

initial_state = InvestigationState(
    incident_description="Alert Triggered: CPUThrottling. Target: cartservice-5766c97c79-lbc86. Description: Pod cartservice-5766c97c79-lbc86 is being heavily CPU throttled.",
    hypotheses=[],
    evidence=[],
    suspect_components=[],
    next_node=0,
    iteration_count=0
)

try:
    step = 0
    for output in agent_graph.stream(initial_state):
        step += 1
        for node_name, node_output in output.items():
            print(f"\n  --- Step {step}: Node '{node_name}' completed ---")
            if isinstance(node_output, dict):
                print(f"    next_node    = {node_output.get('next_node', 'N/A')}")
                print(f"    confidence   = {node_output.get('confidence', 'N/A')}")
                print(f"    hypotheses   = {len(node_output.get('hypotheses', []))} items")
                print(f"    evidence     = {len(node_output.get('evidence', []))} items")
                print(f"    iteration    = {node_output.get('iteration_count', 'N/A')}")
                suspects = node_output.get('suspect_components', [])
                if suspects:
                    print(f"    suspects     = {suspects}")
                rca = node_output.get('final_rca')
                if rca:
                    print(f"\n  🚀 FINAL RCA GENERATED!")
                    import yaml
                    print(yaml.dump(rca, sort_keys=False, default_flow_style=False))
            else:
                print(f"    Raw output: {str(node_output)[:300]}")

    print("\n" + "=" * 60)
    print("✅ PIPELINE COMPLETED SUCCESSFULLY")
    print("=" * 60)

except Exception as e:
    print(f"\n  ❌ PIPELINE FAILED at step {step}: {e}")
    traceback.print_exc()
