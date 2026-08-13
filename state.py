from pydantic import BaseModel
from typing import List, Optional, Any , Annotated
import operator

class AgentState(BaseModel):
    query: str = ""
    results: List[Any] = []
    page_content: List[Any] = []
    sentiment: List[Any] = []
    competitors: List[Any] = []
    reasoning: Annotated[str, operator.add] = ""
    market_trends: Any = {}
    competitors_data: List[Any] = []
    final_report: Optional[str] = None
    llm_feedback : List[str] = []
    retry_count: int = 0
    source : List[str] = []
    has_data : bool = True
    scraped_ratio: float = 0.0


