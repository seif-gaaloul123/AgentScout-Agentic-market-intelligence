from tools import web_search,page_scraping,sentiment_analyser,competitors_extraction ,heavy_model,light_model,better_query
from state import AgentState
import json , time
import concurrent.futures
from concurrent.futures import ThreadPoolExecutor, as_completed

def search_node(state):
    new_query = better_query(state.query)
    reasoning = "[Action]Looking for search results"
    webresults = web_search(new_query)
    reasoning += "[Action]Extracting Competitors"
    page_content,scraped_ratio = page_scraping(webresults)
    content = "\n".join(page_content)
    competitors = competitors_extraction(content[:2000],new_query) #increase it later
    reasoning += "[Observation]Competitors extracted Successfully"
    url_content = []
    for extracted_url in webresults:
        url_content.append(extracted_url['url'])
    has_data = bool(content) or bool(competitors) #so we dont have to pass to all other nodes if we have no data
    return {
        "competitors": competitors,
        "reasoning": reasoning,
        "results": webresults,
        "query": new_query,
        "source" :url_content,
        "has_data":has_data,
        "scraped_ratio" : scraped_ratio
    }

def data_check_router(state):
    if not state.has_data and state.scraped_ratio == 0:
        return "insuffecient_data"
    return ["research", "market_trends"]   

def insuffecient_data(state):
    reasoning = "[Observation]No Competitors or Content found"
    return {
        "reasoning": reasoning,
        "final_report" : None
    }   
def research_node(state):
    
    competitors = state.competitors
    thread_reasoning = "[Action] Initiating parallel competitor research pipeline..."
    logs = {}

    def run_parallel(c):
        thread_reasoning = f"[Action] Checking customer reviews for {c}..."
        query = f"{c} customer reviews pros cons complaints"
        scraped_data , _ = page_scraping(web_search(query))
        truncated_text = "\n".join(scraped_data)
        
        reviews = sentiment_analyser(truncated_text)
        thread_reasoning += f"[Observation] Customer reviews checked for {c}."
        thread_reasoning += f"[Action] Researching competitor positioning for {c}..."
        scraped, _ = page_scraping(web_search(f"{c} pricing news strengths weaknesses 2024 2025"))
        scraped_content = "\n".join(scraped)
        thread_reasoning += f"[Observation] Competitor web data retrieved for {c}."
        time.sleep(1) 
        
        prompt = f"""You are a senior market intelligence analyst.
Analyze the scraped data provided at the end of this prompt.
If data is limited, make reasonable inferences.

CRITICAL LOGIC & FILTERING RULES:
- If any metric or field (such as pricing/prices, strengths, weaknesses, or news) is missing or cannot be verified from the data, do NOT use placeholder values like "Unknown", "Not available", "None identified", "N/A", or "No data".
- Instead, leave that list completely empty (e.g. `[]`) or omit the key entirely.

CRITICAL: Return ONLY valid JSON. No notes, no explanation, no text outside the JSON brackets, matching this schema:
{{
    "competitors_data": [
        {{
            "name": "STRING_PLACEHOLDER",
            "news": ["news point"],
            "prices": ["pricing info"],
            "strengths": ["strength"],
            "weaknesses": ["weakness"]
        }}
    ]
}}

====================
[DYNAMIC INPUT DATA]
Competitor Name: {c}
Scraped Data & Reviews:
{scraped_content[:4000]} + {reviews}
"""
        output = light_model.invoke(prompt).content
        cleaned = output.replace("```json", "").replace("```", "").strip()
        parsed = {"competitors_data": []}
        if cleaned and cleaned.startswith("{"):
            try:
                parsed = json.loads(cleaned)
            except json.JSONDecodeError:
                print(f" JSON parsing failed on competitor {c}. Cleaned string was: {cleaned}")
                parsed = {"competitors_data": [{"name": c, "news": [], "prices": [], "strengths": [], "weaknesses": []}]}
        else:
            parsed = {"competitors_data": [{"name": c, "news": [], "prices": [], "strengths": [], "weaknesses": []}]}

        logs[c] = thread_reasoning
        
        return {"parsed": parsed, "reviews": reviews, "competitor": c}

    all_competitors_data = []
    all_sentiments = [] 

    if not competitors:
        thread_reasoning += "[Observation] No competitors identified to analyze."
        return {
            "competitors_data": [],
            "sentiment": [],
            "reasoning": thread_reasoning
        }

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(competitors)) as executor:
        future_to_competitor = {executor.submit(run_parallel, c): c for c in competitors}
        for future in concurrent.futures.as_completed(future_to_competitor):
            c = future_to_competitor[future]
            try:
                result = future.result()
                all_competitors_data.extend(result["parsed"].get("competitors_data", []))
                all_sentiments.append(result["reviews"])
                thread_reasoning += logs.get(c, "")
            except Exception as exc:
                thread_reasoning += f"[Warning] Execution thread for {c} crashed: {exc}"
                all_competitors_data.append({"name": c, "news": [], "prices": [], "strengths": [], "weaknesses": []})

    thread_reasoning += "[Observation] Concurrent competitor research pipeline executed successfully."
    
    return {
        "competitors_data": all_competitors_data,
        "sentiment": all_sentiments,
        "reasoning": thread_reasoning
    }

def market_trends_node(state) : 
    reasoning = "[Action]Researching market trends"
    query = f"market trends about {state.query}"
    scraped_list , _ = page_scraping(web_search(query))
    trends = "\n".join(scraped_list)[:5000]
    prompt = f"""You are a senior market intelligence analyst.
    Based on the following market research data:
    {trends}
    Analyze and return JSON only:
    {{
        "market_trends": {{
            "market_size": "Provide the financial dollar amount/metric, or return 'unknown' if not explicitly stated in the text",
            "growth_rate": "growth trend (growing/stable/declining) with reason",
            "key_trends": ["trend 1", "trend 2", "trend 3"],
            "opportunities": ["opportunity 1", "opportunity 2"],
            "threats": ["threat 1", "threat 2"],
            "summary": "2-3 sentence overall market assessment"
        }}
    }}
    No markdown, no explanation, JSON only."""

    inference = light_model.invoke(prompt).content
    cleaned_inference = inference.replace("```json", "").replace("```", "").strip()
    try :
        parsed = json.loads(cleaned_inference)
    except json.JSONDecodeError :
        parsed = {"market_trends": {}}
    reasoning += "[Observation]Market trends researched successfully"
    return {
        "market_trends": parsed.get('market_trends', {}),
        "reasoning": reasoning
    }

def synthesize(state):
    reasoning = "[Action]Synthesizing the report"
    judge_prompt = ""
    if state.llm_feedback:
        judge_prompt = f"""
 PREVIOUS REPORT WAS REJECTED — YOU MUST FIX THESE SPECIFIC ISSUES:
{state.llm_feedback}
Explicitly address each point above in this new report before anything else."""

    prompt = f"""You are a Lead Systems Architect, Principal Product Engineer, and Quantitative Business Strategist.
Your task is to synthesize a deeply technical, hyper-realistic Market Intelligence Report based on the provided user query and the retrieved web research context.

{judge_prompt}

TARGET AUDIENCE ANCHORS (Write exclusively for these profiles):

PRODUCT MANAGERS & BUILDERS: They demand technical constraints, explicit feature gaps, architectural challenges, and niche software tool integrations.

BUSINESS ANALYSTS & CONSULTANTS: They demand hard metrics, business model realities, unit economics, and structural market gaps.

STARTUP OWNERS & OPERATORS: They demand actionable, low-fluff operational steps, specific monetization mechanics, and pricing models.

══════════════════════════════════════════════════════════════════════════
CRITICAL ANTI-FLUFF & ANTI-GENERIC PROTOCOL:
You are strictly forbidden from giving generic, high-level business advice or using empty, passive verbs. Every recommendation, observation, and analysis must be translated into an engineering or operational blueprint.

 THE FORBIDDEN WORD LIST (NEVER USE):

"Robust", "Scalable", "Leverage", "Focus", "Optimize", "Strategic", "Synergy", "Partner", "Data-driven", "Robust", "Comprehensive", "Seamless", "Best-in-class", "Customer-centric", "Dynamic".

 THE "TOOL-MANDATORY" CONSTRAINT:

Every recommendation must name specific technology, frameworks, APIs, or regulatory standards. If you find yourself wanting to write a generic sentence, delete it. It is better to have a shorter report with 100% technical density than a longer report with fluff.

 THE "EMPTY ADMISSION" PROTOCOL:

If the research context does not provide enough data to form a specific technical recommendation, you are forbidden from guessing. You must explicitly state: "Insufficient technical data available to formulate a specific recommendation for this section."

Study this Translation Matrix to understand the required depth and style. Note how the examples are framed around a mock Maritime IoT platform in Rotterdam—you must replicate this EXACT level of depth for whatever topic the user actually queried:

SURFACE-LEVEL FLUFF (ABSOLUTELY FORBIDDEN):

"Develop a robust AI-powered solution."

"Explore government funding opportunities."

"Implement a data-driven approach using analytics."

"Leverage cloud services to manage scaling."

"Focus on customer retention and onboarding."

DEEP TECHNICAL SPEC (MANDATORY WRITING STYLE - APPLIED TO CLIENT TOPIC):

"Deploy a localized, quantized Llama-3-8B model hosted on a self-hosted vLLM engine, bypassing API billing limitations by leveraging local bare-metal GPU leases."

"Establish a physical entity under regional customs frameworks (e.g., the Maritime Trade Act) to secure local corporate tax relief, state-backed logistics grants, and foreign currency capital clearances."

"Deploy an asynchronous event queue using Redis and Celery inside FastAPI middleware to track real-time payload delivery metrics and isolate user drop-off points."

"Implement a TimescaleDB hypertable partition scheme to index high-throughput GPS telemetry data streams, cutting database query latency for geographic bounding boxes by 42%."

"Build a conditional onboarding flow using telemetry hooks in React that dynamically triggers hands-on tutorials if a database connection string is not verified within 180 seconds."
══════════════════════════════════════════════════════════════════════════

ANTI-PARROT GUARDRAIL:
Do NOT copy, reference, or use the literal concepts or phrasing from the "DEEP TECHNICAL SPEC" examples above (such as "vLLM", "Llama-3-8B", "Maritime Trade Act", "TimescaleDB", "FastAPI middleware", "Celery", or "Zustand") unless they are directly, explicitly mentioned in the retrieved research context below.

CRITICAL LOGIC & FILTERING RULES:

STRICT RELEVANCY FILTERING (Anti-Noise):
Evaluate all retrieved web context carefully. If a piece of information, company, or news article does not directly align with the specific geographic location, industry vertical, or core intent specified in the user query, discard it entirely.

CRITICAL: Absolutely DO NOT include massive global tech monopolies (such as Google, Amazon, Microsoft, Apple, Meta/Facebook) as competitors or landscape alternatives unless the user explicitly named them in their query. If your context only contains these generic tech giants, discard them completely and state that no direct startup alternatives were identified.

DYNAMIC BULLET GENERATION (The "Unknown" Fix):
Only generate a section or bullet point if you have discovered explicit, verified facts. If data regarding a metric is missing, do NOT print placeholders like "Unknown", "N/A", or "Not available". Instead, completely omit that metric or bullet point.

NO STRAY DOTS OR PLACEHOLDERS:
Do NOT output stray periods, dots, or placeholder characters on their own line between sections. Keep the formatting clean.

SEMANTIC INTENT ALIGNMENT (Anti-Drift):
Analyze the client's query to isolate the core operational or technical "subject". Discard broad, generic business observations that do not directly analyze this targeted subject.

MODERN HASH HEADERS ONLY:
CRITICAL FORMATTING RULE: Do NOT use old-school underlined headers. You must exclusively use standard hash symbols (# for main title, ## for main sections, ### for sub-sections) to style your titles.

THE FOUNDER/OPERATOR PERSPECTIVE:
Translate all market data into actionable operational directives for a team building and selling software.

═══════════════════════════════════════
CLIENT QUERY: {state.query}
═══════════════════════════════════════
COMPETITORS IDENTIFIED: {state.competitors if state.competitors else "None identified"}
═══════════════════════════════════════
COMPETITOR DETAILS & SENTIMENT:
{state.competitors_data}
═══════════════════════════════════════
MARKET TRENDS & OVERVIEW:
{state.market_trends}

REFERENCES:
{state.source}
═══════════════════════════════════════

Now write a professional markdown report with EXACTLY this structure:

Market Research Report

Client Query

State the user's original query clearly.

Executive Summary

Concise overview of market viability and technical realities through the lens of the client's core intent. No business optimism.

Competitor / Alternative Landscape

Profile relevant entities. Omit missing attributes entirely. If no niche competitors exist, state: "No direct niche startup alternatives were identified in the research data."

Market Trends & Opportunities

Bullet points detailing key technical shifts, ecosystem dynamics, or growth vectors. Every bullet must relate back to the core technical subject of the Client Query.

Market Gaps & Challenges

Highlight actual gaps, technical friction points, or business risks identified in the research context. If no specific technical gaps found, state: "Insufficient technical data available."

Strategic Recommendations

Provide exactly 3 concrete, actionable recommendations:

[Task Name]

Operational Action: [Actionable step. Start with a verb: Deploy, Configure, Index, Rewrite, Patch.]

Required Stack: [Name specific tools/libs/frameworks.]

Technical Justification: [Why this specific tool solves the friction point identified in the report.]

Report generated by Market Research Agent""" 
    report = heavy_model.invoke(prompt).content
    
    
    reasoning += "[Observation]Report synthesized successfully"
    return {
        "final_report": report,
        "reasoning": reasoning
    }

MAX_RETRIES = 2

def quality_check(state):
    prompt = f"""You are an expert evaluator for market intelligence reports.

Evaluate this report against the original query.

Original Query: {state.query}
Report: {state.final_report}

Rate each dimension from 1-10:
{{
    "relevance": 8,
    "competitor_depth": 7,
    "actionability": 6,
    "factual_grounding": 8,
    "overall_score": 7,
    "missing": ["pricing data for competitor X", "market size figure"],
    "verdict": "pass or retry or fail"
}}
Return ONLY valid JSON. No markdown, no explanation."""
    output = light_model.invoke(prompt).content
    cleaned = output.replace("```json", "").replace("```", "").strip()
    try:
        content = json.loads(cleaned)
        if content["verdict"] == "retry":
            return {
                "llm_feedback": content["missing"],
                "retry_count": state.retry_count + 1,
            }
        elif content["verdict"] == "fail" :
            return {"llm_feedback" : [],"final_report" :None}
        else:
            return {"llm_feedback": []}

    except Exception as e:
        print(f"Failed to parse quality check score: {e}. Raw output was: {output}")
        return {"llm_feedback": []}

def route_after_quality(state):
    if state.llm_feedback and state.retry_count < MAX_RETRIES:
        return "retry"
    return "end"
        
    




    
   
    
     





    


            
    












   