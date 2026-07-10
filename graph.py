from langgraph.graph import END, START, StateGraph
from nodes import search_node,research_node,market_trends_node,synthesize,quality_check,route_after_quality
from state import AgentState

def agent(query:str):
    graph = StateGraph(AgentState)
    graph.add_node("search",search_node)
    graph.add_node("research",research_node)
    graph.add_node("market_trends",market_trends_node)
    graph.add_node("synthesize",synthesize)
    graph.add_node("quality_check",quality_check)
    graph.add_edge(START, "search")
    graph.add_edge("search","research")
    graph.add_edge("research","market_trends")
    graph.add_edge("market_trends","synthesize")
    graph.add_edge("synthesize","quality_check")
    graph.add_conditional_edges("quality_check", route_after_quality, {
    "retry": "synthesize",
    "end": END})
    workflow = graph.compile()
    initial_state = {
    "query": query,
    "results": [],
    "page_content": [],
    "sentiment": [],
    "competitors": [],
    "reasoning": "",
    "market_trends": [],
    "competitors_data": [],
    "llm_feedback":[],
    "retry_count": 0,
    "final_report": None }
    result = workflow.invoke(initial_state)
    return result["final_report"]

