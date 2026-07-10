from pydantic import BaseModel
from typing import List, Optional, Any

class AgentState(BaseModel):
    query: str = ""
    results: List[Any] = []
    page_content: List[Any] = []
    sentiment: List[Any] = []
    competitors: List[Any] = []
    reasoning: str = ""
    market_trends: Any = {}
    competitors_data: List[Any] = []
    final_report: Optional[str] = None
    llm_feedback : List[str] = []
    retry_count: int = 0


