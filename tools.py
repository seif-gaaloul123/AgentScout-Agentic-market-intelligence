from tavily import TavilyClient
from langchain_groq import ChatGroq
import os
import json
from dotenv import load_dotenv
from scrapling.fetchers import Fetcher
from groq import RateLimitError
from langchain_google_genai import ChatGoogleGenerativeAI



load_dotenv()

light_model = ChatGroq(
    model="llama-3.1-8b-instant", 
    temperature=0)

primary_model = ChatGroq(
    model="meta-llama/llama-4-scout-17b-16e-instruct", 
    temperature=0)

fallback_1 = ChatGroq(
    model="llama-3.3-70b-versatile",
    temperature=0)

heavy_model = primary_model.with_fallbacks(
    fallbacks=[fallback_1],
    exceptions_to_handle=(RateLimitError,))

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
    for i in results:
        try : 
            page = Fetcher.get(i['url'])
            text =page.get_all_text(strip=True,ignore_tags=('script','style','footer','nav'))
            page_content.append(text)
        except Exception as e :
            print(f"Failed to fetch {i['url']}")
            page_content.append("")
    return page_content

def sentiment_analyser(page_content):
    prompt = f"""Analyze reviews about "{page_content}". Return JSON only:
{{"positive": [...], "negative": [...], "overall_sentiment": "positive|negative|mixed", "summary": "..."}}
Reviews: {page_content}"""
    if not page_content:
        return {{"positive": [], "negative": [], "summary": "No data available"}}
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









    


    




       
        


        