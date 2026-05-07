from langchain_core.messages import SystemMessage, HumanMessage
from prompts import VALIDATION_SYSTEM_PROMPT
from agents.llm import build_chat, invoke_with_metrics, merge_metrics


def run_verifier_agent(state):
    chat = build_chat(role="validator")
    messages = [
        SystemMessage(content=VALIDATION_SYSTEM_PROMPT),
        HumanMessage(content=f"""
Red/Threat Agent Output:
{state['red_output']}

Detection and Response Output:
{state['blue_output']}

Verify whether high-fidelity red-team artifacts are covered by detection and response outputs.
"""),
    ]
    content, metric = invoke_with_metrics(chat, messages, "verifier_agent")
    return {
        "verifier_output": content,
        "metrics": merge_metrics(state, metric),
    }
