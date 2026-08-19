from langgraph.graph import END, START, StateGraph
from nodes import search_node,research_node,market_trends_node,synthesize,quality_check,route_after_quality,data_check_router,insuffecient_data
from state import AgentState
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
import os
import sys
import asyncio

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

def join_node(state):
    return {}

async def agent(query:str,config: dict):
    db_url = os.getenv("DATABASE_URL")
    if os.path.exists("/.dockerenv") and db_url and "localhost" in db_url:
        db_url = db_url.replace("localhost", "host.docker.internal")
    async with AsyncPostgresSaver.from_conn_string(db_url) as checkpointer:
        await checkpointer.setup()
        graph = StateGraph(AgentState)
        graph.add_node("search",search_node)
        graph.add_node("research",research_node)
        graph.add_node("market_trends",market_trends_node)
        graph.add_node("synthesize",synthesize)
        graph.add_node("quality_check",quality_check)
        graph.add_node("insuffecient_data",insuffecient_data)     
        graph.add_edge(START, "search")
        graph.add_conditional_edges("search",data_check_router,{"insuffecient_data": "insuffecient_data",
        "sufficient_data": "research"})
        graph.add_edge("insuffecient_data",END)
        graph.add_edge("research", "market_trends")
        graph.add_edge("market_trends","synthesize")
        graph.add_edge("synthesize","quality_check")
        graph.add_conditional_edges("quality_check", route_after_quality, {
        "retry": "synthesize",
        "end": END})
        workflow = graph.compile(checkpointer=checkpointer)        
        initial_state = {
        "query": query,
        "results": [],
        "page_content": [],
        "sentiment": [],
        "competitors": [],
        "reasoning": "",
        "market_trends": {},
        "competitors_data": [],
        "llm_feedback":[],
        "retry_count": 0,
        "source": [],
        "final_report": None }
        result = await workflow.ainvoke(initial_state ,config = config)
        return result["final_report"]

