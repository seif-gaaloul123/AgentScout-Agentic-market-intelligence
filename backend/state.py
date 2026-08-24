from pydantic import BaseModel
from typing import List, Optional, Any, Annotated
import operator

def take_latest(existing, new):
    return new

class AgentState(BaseModel):
    query: str = ""
    results: Annotated[List[Any], take_latest] = []
    page_content: Annotated[List[Any], take_latest] = []
    sentiment: Annotated[List[Any], take_latest] = []
    competitors: Annotated[List[Any], operator.add] = []
    reasoning: Annotated[str, operator.add] = ""
    market_trends: Annotated[Any, take_latest] = {}
    competitors_data: Annotated[List[Any], operator.add] = []
    final_report: Optional[str] = None
    llm_feedback: Annotated[List[str], take_latest] = []
    retry_count: int = 0  
    source: Annotated[List[str], take_latest] = []
    has_data: bool = True
    scraped_ratio: float = 0.0