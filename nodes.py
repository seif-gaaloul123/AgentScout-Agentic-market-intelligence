from tools import web_search,page_scraping,sentiment_analyser,competitors_extraction ,heavy_model,light_model
from state import AgentState
import json , time

state = AgentState()
def search_node(state):
    reasoning = "[Action]Looking for search results"
    webresults = web_search(state.query)
    reasoning += "[Action]Extracting Competitors"
    content = "\n".join(page_scraping(webresults))
    competitors = competitors_extraction(content[:2000],state.query) #increase it later
    reasoning += "[Observation]Competitors extracted Successfully"
    return {
        "competitors": competitors,
        "reasoning": reasoning,
        "results": webresults
    }

def research_node(state):
    competitors = state.competitors
    reasoning = "[Action]Researching competitors and reviewing customer reviews"
    data =[]
    rev = []
    for c in competitors :
        #customer reviews
        reasoning += f"[Action] Checking customer reviews for {c}\n"
        query = f"{c} customer reviews pros cons complaints"
        scraped_data = page_scraping(web_search(query))
        truncated_text = "\n".join(scraped_data)[:3000]
        #while light_model.get_num_tokens(truncated_text) > 8000 :
           # truncated_text = truncated_text[:-500]
        reviews = sentiment_analyser(truncated_text)
        rev.append(reviews)
        reasoning += "[Observation]Customer reviews checked"
        #competitors research
        reasoning += "[Action]Researching competitors"
        scraped = "\n".join(page_scraping(web_search(f"{c} pricing news strengths weaknesses 2024 2025")))[:1500]
        #while light_model.get_num_tokens(scraped) > 8000 :
            #scraped = scraped[:-500]
        data.append(scraped)
        reasoning += "[Observation]Competitors researched successfully"
        time.sleep(5)
        
    reasoning += "[Action]Checking prices/ strengh and weakness of competitors"

    #combined_data = str(data)
    #while light_model.get_num_tokens(combined_data) > 9000:
        # Drop the last 500 chars from the string representation
        #combined_data = combined_data[:-500]

    prompt = f"""You are a senior market intelligence analyst.
Analyze the scraped data below for each competitor.
If data is limited, make reasonable inferences.

CRITICAL LOGIC & FILTERING RULES:
- If any metric or field (such as pricing/prices, strengths, weaknesses, or news) is missing or cannot be verified from the data, do NOT use placeholder values like "Unknown", "Not available", "None identified", "N/A", or "No data".
- Instead, leave that list completely empty (e.g. `[]`) or omit the key entirely.

Data:
{data}

CRITICAL: Return ONLY valid JSON. No notes, no explanation, no text outside the JSON brackets.

{{
    "competitors_data": [
        {{
            "name": "competitor name",
            "news": ["news point"],
            "prices": ["pricing info"],
            "strengths": ["strength"],
            "weaknesses": ["weakness"]
        }}
    ]
}}"""
    output= light_model.invoke(prompt).content
    cleaned = output.replace("```json","").replace("```","").strip() 
    if not cleaned or not cleaned.startswith("{"):
        print(f"LLM failed to return JSON. Raw output was: {output}")
        parsed = {"competitors_data": [{"name": c, "news": [], "prices": [], "strengths": [], "weaknesses": []} for c in competitors]}
    else:
        try :
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            print(f"Failed to parse JSON. Cleaned string was: {cleaned}")
            parsed = {"competitors_data": []}
                
    return {
        "competitors_data": parsed.get('competitors_data', []),
        "sentiment": rev,
        "reasoning": reasoning
    }

def market_trends_node(state) : 
    reasoning = "[Action]Researching market trends"
    query = f"market trends about {state.query}"
    scraped_list = page_scraping(web_search(query))
    trends = "\n".join(scraped_list)[:2000]
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
    parsed = json.loads(cleaned_inference)
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
⚠️ PREVIOUS REPORT WAS REJECTED — YOU MUST FIX THESE SPECIFIC ISSUES:
{state.llm_feedback}
Explicitly address each point above in this new report before anything else."""

    
   # Drop this directly into your synthesis node file (e.g., nodes.py, prompts.py, or graph.py)

    prompt = f"""You are a Lead Systems Architect, Principal Product Engineer, and Quantitative Business Strategist. 
Your task is to synthesize a deeply technical, hyper-realistic Market Intelligence Report based on the provided user query and the retrieved web research context.

{judge_prompt}

TARGET AUDIENCE ANCHORS (Write exclusively for these profiles):
- PRODUCT MANAGERS & BUILDERS: They demand technical constraints, explicit feature gaps, architectural challenges, and niche software tool integrations.
- BUSINESS ANALYSTS & CONSULTANTS: They demand hard metrics, business model realities, unit economics, and structural market gaps.
- STARTUP OWNERS & OPERATORS: They demand actionable, low-fluff operational steps, specific monetization mechanics, and pricing models.

══════════════════════════════════════════════════════════════════════════
⚠️ CRITICAL ANTI-FLUFF GUARDRAIL (THE DEEP REASONING PROTOCOL):
You are strictly forbidden from giving generic, high-level business advice or using empty, passive verbs. Every recommendation, observation, and analysis must be translated into an engineering or operational blueprint.

Study this Translation Matrix to understand the required depth and style. Note how the examples are framed around a mock Maritime IoT platform in Rotterdam—you must replicate this EXACT level of depth for whatever topic the user actually queried:

❌ SURFACE-LEVEL FLUFF (ABSOLUTELY FORBIDDEN):
- "Develop a robust AI-powered solution."
- "Explore government funding opportunities."
- "Implement a data-driven approach using analytics."
- "Leverage cloud services to manage scaling."
- "Focus on customer retention and onboarding."

✔️ DEEP TECHNICAL SPEC (MANDATORY WRITING STYLE - APPLIED TO CLIENT TOPIC):
- "Deploy a localized, quantized Llama-3-8B model hosted on a self-hosted vLLM engine, bypassing API billing limitations by leveraging local bare-metal GPU leases."
- "Establish a physical entity under regional customs frameworks (e.g., the Maritime Trade Act) to secure local corporate tax relief, state-backed logistics grants, and foreign currency capital clearances."
- "Deploy an asynchronous event queue using Redis and Celery inside FastAPI middleware to track real-time payload delivery metrics and isolate user drop-off points."
- "Implement a TimescaleDB hypertable partition scheme to index high-throughput GPS telemetry data streams, cutting database query latency for geographic bounding boxes by 42%."
- "Build a conditional onboarding flow using telemetry hooks in React that dynamically triggers hands-on tutorials if a database connection string is not verified within 180 seconds."
══════════════════════════════════════════════════════════════════════════

⚠️ ANTI-PARROT GUARDRAIL:
Do NOT copy, reference, or use the literal concepts or phrasing from the "DEEP TECHNICAL SPEC" examples above (such as "vLLM", "Llama-3-8B", "Maritime Trade Act", "TimescaleDB", "FastAPI middleware", "Celery", or "Zustand") unless they are directly, explicitly mentioned in the retrieved research context below. 

You must translate the *style, precision, and architectural depth* of these examples to the actual, retrieved realities of the user's specific query.

CRITICAL LOGIC & FILTERING RULES:

1. STRICT RELEVANCY FILTERING (Anti-Noise):
   Evaluate all retrieved web context carefully. If a piece of information, company, or news article does not directly align with the specific geographic location, industry vertical, or core intent specified in the user query, discard it entirely. Do NOT include irrelevant global entities just because they share a keyword match.

   ⚠️ CRITICAL: Absolutely DO NOT include massive global tech monopolies (such as Google, Amazon, Microsoft, Apple, Meta/Facebook) as competitors or landscape alternatives unless the user explicitly named them in their query, or they are direct, literal, feature-for-feature competitors to the specific startup product mentioned. If your context only contains these generic tech giants, discard them completely and state that no direct startup alternatives were identified.

2. DYNAMIC BULLET GENERATION (The "Unknown" Fix):
   When profiling competitors, alternatives, or market metrics, only generate a section or bullet point if you have discovered explicit, verified facts in the context. If data regarding a metric (such as pricing, weaknesses, or customer sentiment) is missing, do NOT print placeholders like "Unknown", "N/A", or "Not available". Instead, completely omit that metric or bullet point from the output.

3. NO STRAY DOTS OR PLACEHOLDERS:
   Do NOT output stray periods, dots, or placeholder characters (such as "." or "N/A") on their own line between sections, list items, or anywhere in the report. Keep the formatting clean and continuous.

4. SEMANTIC INTENT ALIGNMENT (Anti-Drift Guardrail):
   Analyze the client's query to isolate the core operational or technical "subject" (e.g., if the query asks about "integrations", focus strictly on technical stacks, APIs, and software pipelines. If it asks about "marketing channels", focus strictly on user acquisition methods).
   Discard broad, generic business observations that do not directly analyze this targeted operational subject. Every insight, trend, and recommendation must be anchored to this core subject.

5. MODERN HASH HEADERS ONLY (Anti-Line Formatting Guardrail):
   ⚠️ CRITICAL FORMATTING RULE: Do NOT use old-school underlined headers (where text is followed by a line of `======` or `------` on the next line). You must exclusively use standard hash symbols (`#` for main title, `##` for main sections, `###` for sub-sections) to style your titles and sections. 

6. THE FOUNDER/OPERATOR PERSPECTIVE:
   The target reader of this report is a STARTUP FOUNDER/OPERATOR, not an investor. 
   Do not write about "underwriting," "investment caution," or "due diligence." 
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
═══════════════════════════════════════

Now write a professional markdown report with EXACTLY this structure:

# Market Research Report

## Client Query

State the user's original query clearly to establish context.

## Executive Summary

A concise overview of the market viability, major findings, and high-level conclusions. This must summarize the findings specifically through the lens of the client's core query intent, emphasizing technical and operational realities over generic startup optimism.

## Competitor / Alternative Landscape

Profile the relevant entities found.

* REMINDER: Exclude Big Tech giants (Google, Amazon, etc.) unless they are direct, specific niche product matches.

* For each entity, only list the attributes (e.g., Positioning, Strengths, Weaknesses, Pricing, Recent News, Customer Sentiment) where explicit data exists. Omit any missing fields entirely.

* If no direct niche competitors were identified, state: "No direct niche startup alternatives were identified in the research data."

## Market Trends & Opportunities

Bullet points detailing key trends, ecosystem dynamics, or growth vectors supported by the context. Every bullet point must directly relate back to the core technical or operational subject of the Client Query. Focus on integration patterns, tech stack migrations, and customer behavioral shifts.

## Market Gaps & Challenges

Highlight actual gaps, technical friction points, or business risks identified in the research context. Avoid generic market risks; list specific, grounded technical, structural, or pricing blockers.

## Strategic Recommendations

Provide actionable, numbered recommendations (minimum 3 concrete, actionable recommendations) tailored directly to answering the user's query based on the findings.

* Each recommendation must be structured with three distinct sub-components:
  1. **Operational/Technical Action:** A concrete, highly descriptive task outlining *what* to build or execute (no generic verbs like "leverage" or "use" without specific, named technical tooling, SDKs, APIs, or regulatory frameworks).
  2. **Stack & Tooling Blueprint:** Recommend specific tools, libraries, architectural configurations (e.g., PostgreSQL schema design, custom proxy servers, Stripe Billing API, local hosting, regional startup portals) and explain exactly how they integrate.
  3. **Justification & Gap Alignment:** Justify how this recommendation solves a specific friction point, technical gap, or local constraint identified in the "Market Gaps & Challenges" section of this report.

* Strictly avoid generic business advice or high-level strategic platitudes.

Report generated by Market Research Agent"""
    report = heavy_model.invoke(prompt).content
    
    # Remove stray dots and formatting artifacts (e.g., ".\n2 .\n")
    import re
    cleaned_report = re.sub(r'\n\s*\.\s*\n', '\n', report)
    cleaned_report = re.sub(r'\\n\s*\.\s*(?=\d+\s*\.)', '\\n', cleaned_report)
    cleaned_report = cleaned_report.replace('\\n', '\n')
    
    reasoning += "[Observation]Report synthesized successfully"
    return {
        "final_report": cleaned_report,
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
        else:
            return {"llm_feedback": []}

    except Exception as e:
        print(f"Failed to parse quality check score: {e}. Raw output was: {output}")
        return {"llm_feedback": []}

def route_after_quality(state):
    if state.llm_feedback and state.retry_count < MAX_RETRIES:
        return "retry"
    return "end"
        
    




    
   
    
     





    


            
    












   