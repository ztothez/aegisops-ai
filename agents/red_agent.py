from prompts import RED_SYSTEM_PROMPT
from mitre import get_technique_details
from langchain_core.messages import SystemMessage, HumanMessage
from agents.llm import build_chat, invoke_with_metrics, merge_metrics


def run_red_agent(state):
    chat = build_chat()
    technique_details = get_technique_details(state["technique_id"])
    messages = [
        SystemMessage(content=RED_SYSTEM_PROMPT),
        HumanMessage(content=f"""
Generate a high-fidelity authorized purple-team simulation for this MITRE ATT&CK technique:

{technique_details}

Make the output technically detailed enough for detection engineering.
Use the exact section names from the system prompt.
Do not output "Defensive Scope" or vague safe-only language.
Include advanced known ATT&CK-style behavior when relevant, but do not invent zero-day vulnerabilities or unknown exploit chains.
For each phase, include detection-useful commands_or_patterns, telemetry, process behavior, and observables.
Include the required "## Exploit Code" section and the "exploit_code" JSON field.
Return only the requested markdown sections and JSON block.
"""),
    ]
    content, metric = invoke_with_metrics(chat, messages, "red_agent")
    return {
        "red_output": content,
        "metrics": merge_metrics(state, metric),
    }
