from prompts import BLUE_SYSTEM_PROMPT
from langchain_core.messages import SystemMessage, HumanMessage
from agents.llm import build_chat, invoke_with_metrics, merge_metrics


def run_blue_agent(state):
    chat = build_chat()
    messages = [
        SystemMessage(content=BLUE_SYSTEM_PROMPT),
        HumanMessage(content=f"""
Technique ID: {state['technique_id']}

Red/Threat Agent Output:
{state['red_output']}

Convert the exact red-team simulation artifacts into Sigma-style detection logic.
Use all JSON observables where possible and explicitly call out any gap.
Do not collapse the rule into only generic process names if richer command, process, file, registry, or network indicators are present.
Include the required "## Real-Time Detection Plan" section for SIEM/EDR streaming alerts.
"""),
    ]
    content, metric = invoke_with_metrics(chat, messages, "blue_agent")
    return {
        "blue_output": content,
        "metrics": merge_metrics(state, metric),
    }
