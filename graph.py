from langgraph.graph import StateGraph, START, END
from typing import Optional, TypedDict
from agents.red_agent import run_red_agent
from agents.blue_agent import run_blue_agent
from agents.response_agent import run_response_agent
from agents.verifier_agent import run_verifier_agent


class AgentState(TypedDict, total=False):
    technique_id: str
    red_output: str
    blue_output: str
    response_output: Optional[str]
    verifier_output: Optional[str]
    metrics: dict


graph = StateGraph(AgentState)
graph.add_node("red_agent", run_red_agent)
graph.add_node("blue_agent", run_blue_agent)
graph.add_node("response_agent", run_response_agent)
graph.add_node("verifier_agent", run_verifier_agent)
graph.add_edge(START, "red_agent")
graph.add_edge("red_agent", "blue_agent")
graph.add_edge("blue_agent", "response_agent")
graph.add_edge("response_agent", "verifier_agent")
graph.add_edge("verifier_agent", END)
app = graph.compile()
