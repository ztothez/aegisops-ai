from prompts import RESPONSE_SYSTEM_PROMPT
from langchain_core.messages import SystemMessage, HumanMessage
from agents.llm import build_chat, invoke_with_metrics, merge_metrics


def run_response_agent(state):
    chat = build_chat(role="response")
    messages = [
        SystemMessage(content=RESPONSE_SYSTEM_PROMPT),
        HumanMessage(content=f"""
Technique ID: {state['technique_id']}

Red/Threat Agent Output:
{state['red_output']}

Blue/Detection Agent Output:
{state['blue_output']}

Generate response guidance that references the exact simulation telemetry and detection logic.
Return the required "## Response Guidance" section with concrete triage, containment, hunt, mitigation, escalation, and reporting actions.
"""),
    ]
    content, metric = invoke_with_metrics(chat, messages, "response_agent")
    return {
        "response_output": content,
        "blue_output": f"{state['blue_output']}\n\n{content}",
        "metrics": merge_metrics(state, metric),
    }
