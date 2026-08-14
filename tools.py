from tavily import TavilyClient
import os
import json
from dotenv import load_dotenv
from scrapling.fetchers import Fetcher
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage, AIMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatResult, ChatGeneration
import requests


load_dotenv()


def load_cloudflare_credentials(path: str | None = None) -> list[tuple[str, str]]:
    """Parse keys.txt into (account_id, api_key) pairs.

    Layout per block:
        <account_id>
        <api_key>
        --

    The '--' line is an optional separator between blocks.
    """
    if path is None:
        path = os.path.join(os.path.dirname(__file__), "keys.txt")

    with open(path) as f:
        blocks = [b.strip() for b in f.read().split("--") if b.strip()]

    credentials: list[tuple[str, str]] = []
    for block in blocks:
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if len(lines) >= 2:
            credentials.append((lines[0], lines[1]))

    return credentials


class CloudflareRotateChatModel(BaseChatModel):
    model_name: str
    credentials: list[tuple[str, str]]
    _current_index: int = 0

    def _generate(self, messages: list[BaseMessage], stop: list[str] | None = None, **kwargs) -> ChatResult:
        formatted_messages = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                role = "system"
            elif isinstance(msg, HumanMessage):
                role = "user"
            else:
                role = "assistant"
            formatted_messages.append({"role": role, "content": msg.content})

        payload = {"messages": formatted_messages}

        attempts = len(self.credentials)
        last_error = None

        for _ in range(attempts):
            account_id, token = self.credentials[self._current_index]
            print(f"CURRENT CREDENTIAL BEING TRIED (Index {self._current_index}) account={account_id}")
            headers = {"Authorization": f"Bearer {token}"}
            url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{self.model_name}"

            try:
                response = requests.post(url, headers=headers, json=payload)

                if response.status_code in [429, 403]:
                    print(f"Rate limit hit on credential index {self._current_index}. Rotating account + key...")
                    self._current_index = (self._current_index + 1) % len(self.credentials)
                    continue

                response.raise_for_status()
                res_json = response.json()

                content = res_json.get("result", {}).get("response", "")

                message = AIMessage(content=content)
                generation = ChatGeneration(message=message)
                return ChatResult(generations=[generation])

            except Exception as e:
                last_error = e
                self._current_index = (self._current_index + 1) % len(self.credentials)

        raise RuntimeError(f"All Cloudflare credentials exhausted or request failed. Last error: {last_error}")

    @property
    def _llm_type(self) -> str:
        return "cloudflare-rotate"


credentials = load_cloudflare_credentials()
print(f"PARSED CREDENTIALS COUNT: {len(credentials)}")

if credentials:
    heavy_model = CloudflareRotateChatModel(
        model_name="@cf/google/gemma-4-26b-a4b-it",
        credentials=credentials
    )
    light_model = CloudflareRotateChatModel(
        model_name="@cf/meta/llama-3.1-8b-instruct-fp8",
        credentials=credentials
    )
else:
    raise ValueError("No Cloudflare credentials (account_id + api_key pairs) found in keys.txt")


def better_query(query:str):
    prompt = f"""You are an expert search query strategist and research assistant. 
Your goal is to transform a user's brief, high-level search phrase into a deep, highly specific research question optimized for web search engines and LLM-driven analysis agents.

Instructions:
1. **Expand Context**: Identify the underlying business, economic, or technical intent behind the query.
2. **Add Dimensions**: Explicitly hint at core metrics, competitive dynamics, market implications, or regional nuances (if a location is implied or contextually relevant).
3. **Remove Ambiguity**: Turn vague keywords into a structured, explicit question.
4. **Constraint**: Output **ONLY** the rewritten research question. Do not include conversational filler, preamble, introductory remarks, or quotation marks.

Examples:
- User: "coffee shop delivery"
  Rewrite: "Should I add a delivery service to an existing coffee shop business in Tunisia? What are the local competitive dynamics, operational margin implications, and logistics challenges?"

- User: "best python backend framework 2026"
  Rewrite: "What are the top-performing Python backend frameworks in 2026, comparing FastAPI, Django, and modern asynchronous alternatives in terms of performance, async support, and ecosystem maturity?"

User Query: "{query}"
"""
    new_query = light_model.invoke(prompt).content
    return new_query

def web_search(query:str,max_results:int=3):
    try:
        client = TavilyClient(api_key=os.getenv("TAVILY_API_KEY"))
        response = client.search(
            query=query,
            max_results=max_results
        )
        results = response['results']
        return results
    except Exception as e:
        print(f"Failed to fetch web search results: {e}")
        return []
   
   
def page_scraping(results):
    page_content =[]
    content_count = 0
    for i in results:
        try : 
            page = Fetcher.get(i['url'])
            text =page.get_all_text(strip=True,ignore_tags=('script','style','footer','nav'))
            page_content.append(text)
            content_count += 1
        except Exception as e :
            print(f"Failed to fetch {i['url']}")
            page_content.append("")
    scraped_ratio = content_count/len(results) if results else 0       
    return page_content , scraped_ratio

def sentiment_analyser(page_content):
    truncated = page_content[:6000] if isinstance(page_content, str) else str(page_content)[:6000]
    prompt = f"""Analyze reviews about "{truncated}". Return JSON only:
{{"positive": [...], "negative": [...], "overall_sentiment": "positive|negative|mixed", "summary": "..."}}
Reviews: {truncated}"""
    if not page_content:
        return {"positive": [], "negative": [], "summary": "No data available"}
    else:
        output = light_model.invoke(prompt).content
        cleaned = output.replace("```json", "").replace("```", "").strip()
        try:
            parsed = json.loads(cleaned)
            return parsed
        except json.JSONDecodeError:
            print(f"Failed to parse JSON. Cleaned string was: {cleaned}")
            return {"positive": [], "negative": [], "summary": "No data available"}

def competitors_extraction(page_content,query):
    prompt = f"""Based on the query: "{query}"
Extract only the names of companies, startups, or specific entities mentioned in the text that are actual competitors or relevant actors operating in, targeting, or directly related to the specific geographic region and industry sector of the query.

Strict Relevancy Rules:
1. Only extract entities that are directly relevant to the core geographic region and industry specified in the query (e.g., if the query is about starting an AI startup in Tunisia, only extract entities that are AI companies/startups in Tunisia, or active investors/players in the Tunisian AI ecosystem).
2. DO NOT extract unrelated global entities, general websites, coding bootcamps (like Nucamp), or generic tools mentioned in passing unless they are primary local competitors or ecosystem actors.
3. Return ONLY a valid JSON array of strings. No explanation, no markdown, no extra text.
Example output: ["InstaDeep", "Addvocate.AI"]

Text: {page_content}"""
    if not page_content:
        return []
    else:
        output = light_model.invoke(prompt).content
        cleaned = output.replace("```json", "").replace("```", "").strip()
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, list):
                return parsed
            else:
                print(f"LLM returned non-list for competitors: {cleaned}")
                return []
        except Exception as e:
            print(f"Failed to parse competitors JSON: {e}. Raw output: {output}")
            return []









    


    




       
        


        